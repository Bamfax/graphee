#!/usr/bin/env python
# coding=utf-8

import os, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib", "../lib"))
import re, json
from helperfuncs import string_hascontent, string_preformat

#------------------   def get_splunklib_config(): start  -----------------#
# Helper method to get config settings with error checking (originally from TA-Virustotal)
def get_splunklib_config(self, conffile, stanza, key, thetype, errormsg=None):
    try:
        return thetype( self.service.confs[str(conffile)][str(stanza)][str(key)] )
    except:
        if errormsg == None or str(errormsg).strip() == '':
            self.error_exit( sys.exc_info(), 'ERROR: Getting config with app  %s stanza %s and key %s. '
                                                'Error: %s' % ( conffile, stanza, key, sys.exc_info() ) )
        else:
            self.error_exit( sys.exc_info(), str( errormsg ) )
#------------------   def get_splunklib_config(): end  -----------------#

#------------------   def prepare(): start             -----------------#
def sharedprepare(self):
    """
    Shared prepare for all custom commands
    :return: None
    """
    self.logger.info('started sharedprepare(): %s', self)

    app_id = 'graphee'
    conf_uris_page     = app_id + '_uris'                        # = 'graphee_uris'
    conf_accounts_page = app_id + '_accounts'                    # = 'graphee_accounts'
    neo4j_uri = {}
    neo4j_account = {}
    noact = self.noact
    uri = self.uri

    # Lookup the neo4j uri:
    desired_uri_stanza = uri
    neo4j_uri['conf_uri_stanza_name'] = get_splunklib_config( self, conf_uris_page, desired_uri_stanza, 'name',      str, "Could not find the specified uri id \"%s\"" % ( desired_uri_stanza ) )
    neo4j_uri['uri']                  = get_splunklib_config( self, conf_uris_page, desired_uri_stanza, 'neo4j_uri', str, "Could not find the specified uri id \"%s\"" % ( desired_uri_stanza ) )

    # Lookup the neo4j account:
    # 1. Get the username from config
    # 2. Get the matching password from storage_passwords

    # 1. Get the username from config
    desired_account_stanza = self.account
    neo4j_account['conf_account_stanza_name'] = get_splunklib_config( self, conf_accounts_page, desired_account_stanza, 'name',             str, "Could not find the specified account id \"%s\"" % ( desired_account_stanza ) )
    neo4j_account['username']                 = get_splunklib_config( self, conf_accounts_page, desired_account_stanza, 'account_username', str, "Could not find the specified account id \"%s\"" % ( desired_account_stanza ) )
    desired_neo4j_account_id = neo4j_account['conf_account_stanza_name']

    # 2. Get the matching password from storage_passwords
    #desired_neo4j_account_path = '__REST_CREDENTIAL__#graphite#configs/conf-' + CONF_ACCOUNTS_PAGE + ':' + desired_neo4j_account_id + '``splunk_cred_sep``1:'
    desired_neo4j_account_path = str('__REST_CREDENTIAL__#{0}#configs/conf-{1}:{2}``splunk_cred_sep``1:').format(app_id, conf_accounts_page, desired_neo4j_account_id)
    storage_password = self.service.storage_passwords[desired_neo4j_account_path]

    try:
        storage_password_username = storage_password['username']
        stanza_name = re.search('^([^`]+)', storage_password_username).group(1)
        neo4j_account['storage_stanza_name'] = stanza_name
        neo4j_account['path'] = storage_password['path']
        neo4j_account['realm'] = storage_password['realm']
        neo4j_account['password'] = json.loads(storage_password['clear_password'])['account_password']
    except Exception as ex:
        exceptiondesc = str( type(ex).__name__ )
        errormsg = ( 'Error reading and setting the DBMS account. This can happen if the app configuration '
                     'was not supplied with a DBMS account yet or account specified on the  does not exist. '
                     'Exception: %s' % ( exceptiondesc ) )
        self.error_exit( sys.exc_info(), errormsg )

    self.logger.debug( 'sharedprepare() done.' )

    return app_id, conf_uris_page, conf_accounts_page, neo4j_uri, neo4j_account, noact
#------------------   def prepare(): end               -----------------#