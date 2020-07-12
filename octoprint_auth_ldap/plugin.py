# coding=utf-8
from __future__ import absolute_import

from octoprint.plugin import TemplatePlugin, RestartNeedingPlugin
from octoprint.settings import settings
from octoprint_auth_ldap.constants import DEFAULT_ADMIN_GROUP, DEFAULT_USER_GROUP, OU_FILTER, OU_MEMBER_FILTER, OU, \
    REQUEST_TLS_CERT, SEARCH_BASE, URI
from octoprint_auth_ldap.ldap import LDAPConnection
from octoprint_auth_ldap.tweaks import SettingsPlugin
from octoprint_auth_ldap.user_manager import LDAPUserManager


class AuthLDAPPlugin(SettingsPlugin, TemplatePlugin, RestartNeedingPlugin):
    # noinspection PyUnusedLocal,PyShadowingNames
    def ldap_user_factory(self, components, settings):
        self._user_manager = LDAPUserManager(plugin=self, ldap=LDAPConnection(plugin=self))
        return self._user_manager

    # Softwareupdate hook

    def check_config(self):
        return dict(
            auth_ldap=dict(
                displayName=self._plugin_name,
                displayVersion=self._plugin_version,

                # version check: github repository
                type="github_release",
                user="gillg",
                repo="OctoPrint-LDAP",
                current=self._plugin_version,

                # update method: pip
                pip="https://github.com/gillg/OctoPrint-LDAP/archive/{target_version}.zip"
            )
        )

    # SettingsPlugin

    def get_settings_defaults(self):
        return dict(
            auth_password=None,
            auth_user=None,
            default_admin_group=False,
            default_user_group=True,
            ou_filter="ou=%s",
            ou_member_filter="uniqueMember=%s",
            ou=None,
            local_cache=False,
            request_tls_cert=None,
            search_base=None,
            search_filter="uid=%s",
            search_term_transform=None,
            uri=None,
            userid_field=None,
            userid_pattern=None
        )

    def get_settings_restricted_paths(self):
        return dict(
            admin=self.get_settings_defaults().keys(),
            user=[],
            never=[]
        )

    def get_settings_version(self):
        return 3

    def on_settings_migrate(self, target, current):
        if target != current:
            self._logger.info(
                "Migrating %s settings from version %s to version %s" % (self._plugin_name, current, target))
            if current is None:
                self.migrate_settings_1_to_2()
            if current != 3:  # intentional fall-through to bring None _and_ 2 to 3 (my kingdom for a switch statement!)
                self.migrate_settings_2_to_3()

    def migrate_settings_1_to_2(self):
        # changing settings location to plugin standard location and renaming to simplify access
        self._logger.debug("Attempting to migrate settings from version 1 to version 2")

        # migrate old settings to new locations and erase old settings
        prev_settings = dict(  # prev_setting_name="new_setting_name"
            ldap_uri=URI,
            ldap_tls_reqcert=REQUEST_TLS_CERT,
            ldap_search_base=SEARCH_BASE,
            ldap_groups="groups"
        )
        for prev_key, key in prev_settings.items():
            prev_value = settings().get(["accessControl", prev_key])
            if prev_value is not None:
                cleaned_prev_value = prev_value
                if prev_key == "ldap_tls_reqcert" and prev_value == "demand":
                    cleaned_prev_value = True
                self.settings.set([key], cleaned_prev_value)
                self._logger.info(
                    "accessControl.%s=%s setting migrated to plugins.%s.%s=%s"
                    % (prev_key, prev_value, self._identifier, key, cleaned_prev_value))
            else:
                self._logger.debug('accessControl.%s=None, migration not necessary' % prev_key)
            settings().set(["accessControl", prev_key], None)

    def migrate_settings_2_to_3(self):
        # renaming to get rid of roles in favor of local groups, and clarifying LDAP group settings
        self._logger.debug("Attempting to migrate settings from version 2 to version 3")

        # migrate old settings to new locations and erase old settings
        prev_settings = dict(  # prev_setting_name="new_setting_name"
            default_role_admin=DEFAULT_ADMIN_GROUP,
            default_role_user=DEFAULT_USER_GROUP,
            group_filter=OU_FILTER,
            group_member_filter=OU_MEMBER_FILTER,
            groups=OU
        )
        for prev_key, key in prev_settings.items():
            prev_value = self.settings.get([prev_key])
            if prev_value is not None:
                self.settings.set([key], prev_value)
                self._logger.info(
                    "plugin.%s.%s=%s setting migrated to plugins.%s.%s=%s"
                    % (self._identifier, prev_key, prev_value, self._identifier, key, prev_value))
            else:
                self._logger.debug('plugin.%s.%s=None, migration not necessary' % (self._identifier, prev_key))
            self.settings.set([prev_key], None)

    # TemplatePlugin

    def get_template_configs(self):
        return [dict(type="settings", custom_bindings=False)]
