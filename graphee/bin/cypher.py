#!/usr/bin/env python
# coding=utf-8

import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib", "../lib"))
import re, json, time
from neo4j import GraphDatabase, Result as neo4jResult
from neo4j.graph import Node as neo4jNode
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators
from helperfuncs import string_hascontent, string_preformat

@Configuration( local = True,  streaming = False )
class cypher(GeneratingCommand):
    from classsharedfuncs import sharedprepare
    
    uri = Option(
        doc='''
        **Syntax:** **uri=***<URI_ID>*
        **Description:** URI_ID: ID of the Neo4j URI entry as specified in configuration page under "Neo4j URI" ''',
        require=True, validate=validators.Fieldname() )
 
    account = Option(
        doc='''
        **Syntax:** **account=***<Account_ID>*
        **Description:** Account_ID: ID of the Neo4j Account entry as specified in configuration page under "Neo4j Accounts" ''',
        require=True, validate=validators.Fieldname() )

    noact = Option(
        doc='''
        **Syntax:** **noact=***<"true"|"false">*
        **Description:** No action. Default is \"false\" ''',
        require=False, validate=validators.Boolean(), default='false' )

    mode = Option(
        doc='''
        **Syntax:** **mode=***<"read"|"write">*
        **Description:** Mode for the cypher transaction and command, if it intends to make changes. Choose between \"read\" and \"write\". Default is \"read\" ''',
        require=False, validate=validators.Set('read', 'write'), default='read' )

    query = Option(
        doc='''
        **Syntax:** **account=***<cypher_querysstring>*
        **Description:** Cypher querystring to be executed on the graph db. ''',
        require=True )

    #------------------   def prepare(): start             -----------------#
    def prepare(self):
        """
        Prepare, customcommand specific. 
        :return: None
        """
        self.logger.info('prepare start: %s', self)

        self.app_id, self.conf_uris_page, self.conf_accounts_page, self.neo4j_uri, self.neo4j_accoount, self.noact = self.sharedprepare()
        self.TX_MODE = self.mode
        self.QUERYSTRING = self.query

        if not string_hascontent(self.QUERYSTRING):
            errormsg = ( 'ERROR: In prepare(): Cypher querystring is empty, which it should not be.' )
            self.error_exit( sys.exc_info(), errormsg )

        self.logger.debug( 'prepare() done.' )
    #------------------   def prepare(): end               -----------------#

    #------------------   def runcyphercmd(): start          -----------------#
    def runcyphercmd( self, tx ):
        querystr = self.QUERYSTRING
        results = tx.run( querystr ) 

        out = list()
        if isinstance( results, neo4jResult ):
            for record in results:
                outevent = record.data()
                out.append( outevent )

        self.logger.debug( 'runcyphercmd() done. ' )
        return out
    #------------------   def runcyphercmd(): end            -----------------#

    #------------------   def cyphercmd(): start          -----------------#
    def cyphercmd( self ):
        driver = GraphDatabase.driver( self.neo4j_uri['uri'], auth = ( self.neo4j_accoount['username'], self.neo4j_accoount['password' ]) )

        with driver.session() as session:
            if self.TX_MODE == 'read':
                results = session.execute_read( self.runcyphercmd )
            elif self.TX_MODE == 'write':
                results = session.execute_write( self.runcyphercmd )

        return results

    #------------------   def cyphercmd(): end            -----------------#

    #------------------   def generate(): start            -----------------#
    def generate( self ):
        if self.noact == True:
            text = 'NOACT was true, no action.'
            yield {'_time': time.time(), '_raw': text}
            return

        try:
            finalresults = self.cyphercmd()
            self.logger.debug( 'cyphercmd() returned. ' )

            for event in finalresults:
                yield { **event, '_raw': json.dumps(event) }

        except Exception as ex:
            exdesc_orig = '{0}: {1}: {2}'.format(str(type(ex).__name__), str(ex.args), str(ex.__doc__))
            exdesc_sani = string_preformat(exdesc_orig)
            errormsg =  'ERROR: In generate(): {0}'.format( exdesc_sani )
            self.error_exit( sys.exc_info(), str(errormsg) )
    #------------------   def generate(): end              -----------------#


dispatch( cypher, sys.argv, sys.stdin, sys.stdout, __name__ )
