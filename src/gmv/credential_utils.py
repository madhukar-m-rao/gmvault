'''
    Gmvault: a tool to backup and restore your gmail account.
    Copyright (C) <2011-2013>  <guillaume Aubert (guillaume dot aubert at gmail do com)>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

 Module handling the xauth authentication.
 Strongly influenced by http://code.google.com/p/googlecl/source/browse/trunk/src/googlecl/service.py
 and xauth part of gyb http://code.google.com/p/got-your-back/source/browse/trunk/gyb.py

'''
import gdata.service
import webbrowser
import random
import time
import atom
import urllib
import json

import os
import getpass

import gmv.log_utils as log_utils
import gmv.blowfish as blowfish
import gmv.gmvault_utils as gmvault_utils

LOG = log_utils.LoggerFactory.get_logger('oauth')


def get_2_legged_oauth_tok_sec():
    '''
       Get 2 legged token and secret
    '''
    tok = raw_input('Enter your domain\'s OAuth consumer key: ')
  
    sec = raw_input('Enter your domain\'s OAuth consumer secret: ')
      
    return tok, sec, "two_legged"

#GMVAULT IDENTIFIER
GMVAULT_CLIENT_ID="1070918343777-0eecradokiu8i77qfo8e3stbi0mkrtog.apps.googleusercontent.com"
GMVAULT_CIENT_SECRET="IVkl_pglv5cXzugpmnRNqtT7"

SCOPE='https://mail.google.com/'
# The URL root for accessing Google Accounts.
GOOGLE_ACCOUNTS_BASE_URL = 'https://accounts.google.com'
# Hardcoded dummy redirect URI for non-web apps.
REDIRECT_URI = 'urn:ietf:wg:oauth:2.0:oob'

OAUTH2_URL="https://accounts.google.com/o/oauth2/auth?client_id=%s&redirect_uri=urn%3Aietf%3Awg%3Aoauth%3A2.0%3Aoob&response_type=code&scope=https%3A%2F%2Fmail.google.com%2F"

def get_accounts_url(command):
  """Generates the Google Accounts URL.

  Args:
    command: The command to execute.

  Returns:
    A URL for the given command.
  """
  return '%s/%s' % (GOOGLE_ACCOUNTS_BASE_URL, command)


def escape_url(text):
  # See OAUTH 5.1 for a definition of which characters need to be escaped.
  return urllib.quote(text, safe='~-._')


def unescape_url(text):
  # See OAUTH 5.1 for a definition of which characters need to be escaped.
  return urllib.unquote(text)


def format_url_params(params):
  """Formats parameters into a URL query string.

  Args:
    params: A key-value map.

  Returns:
    A URL query string version of the given parameters.
  """
  param_fragments = []
  for param in sorted(params.iteritems(), key=lambda x: x[0]):
    param_fragments.append('%s=%s' % (param[0], escape_url(param[1])))
  return '&'.join(param_fragments)

def generate_permission_url():
  """Generates the URL for authorizing access.

  This uses the "OAuth2 for Installed Applications" flow described at
  https://developers.google.com/accounts/docs/OAuth2InstalledApp

  Args:
    client_id: Client ID obtained by registering your app.
    scope: scope for access token, e.g. 'https://mail.google.com'
  Returns:
    A URL that the user should visit in their browser.
  """
  params = {}
  params['client_id'] = GMVAULT_CLIENT_ID
  params['redirect_uri'] = REDIRECT_URI
  params['scope'] = SCOPE
  params['response_type'] = 'code'
  return '%s?%s' % (get_accounts_url('o/oauth2/auth'),
                    format_url_params(params))

def get_authorization_tokens(authorization_code):
  """Obtains OAuth access token and refresh token.

  This uses the application portion of the "OAuth2 for Installed Applications"
  flow at https://developers.google.com/accounts/docs/OAuth2InstalledApp#handlingtheresponse

  Args:
    client_id: Client ID obtained by registering your app.
    client_secret: Client secret obtained by registering your app.
    authorization_code: code generated by Google Accounts after user grants
        permission.
  Returns:
    The decoded response from the Google Accounts server, as a dict. Expected
    fields include 'access_token', 'expires_in', and 'refresh_token'.
  """
  params = {}
  params['client_id'] = GMVAULT_CLIENT_ID
  params['client_secret'] = GMVAULT_CIENT_SECRET
  params['code'] = authorization_code
  params['redirect_uri'] = REDIRECT_URI
  params['grant_type'] = 'authorization_code'
  request_url = get_accounts_url('o/oauth2/token')

  response = urllib.urlopen(request_url, urllib.urlencode(params)).read()
  return json.loads(response)

def generate_oauth2_string(username, access_token, base64_encode=True):
  """Generates an IMAP OAuth2 authentication string.

  See https://developers.google.com/google-apps/gmail/oauth2_overview

  Args:
    username: the username (email address) of the account to authenticate
    access_token: An OAuth2 access token.
    base64_encode: Whether to base64-encode the output.

  Returns:
    The SASL argument for the OAuth2 mechanism.
  """
  auth_string = 'user=%s\1auth=Bearer %s\1\1' % (username, access_token)
  if base64_encode:
    auth_string = base64.b64encode(auth_string)
  return auth_string

def get_oauth2_tok_sec(email, use_webbrowser = False, debug=False):
    '''
       Generate token and secret
    '''

    #create permission url
    permission_url = generate_permission_url()

    #message to indicate that a browser will be opened
    raw_input('gmvault will now open a web browser page in order for you to grant gmvault access to your Gmail.\n'\
              'Please make sure you\'re logged into the correct Gmail account (%s) before granting access.\n'\
              'Press ENTER to open the browser. Once you\'ve granted access you can switch back to gmvault.' % (email))

    # run web browser otherwise print message with url
    if use_webbrowser:
        try:
            webbrowser.open(str(permission_url))
        except Exception, err: #pylint: disable-msg=W0703
            LOG.critical("Error: %s.\n" % (err) )
            LOG.critical("=== Exception traceback ===")
            LOG.critical(gmvault_utils.get_exception_traceback())
            LOG.critical("=== End of Exception traceback ===\n")

        verification_code = raw_input("You should now see the web page on your browser now.\n"\
                  "If you don\'t, you can manually open:\n\n%s\n\nOnce you've granted"\
                  " gmvault access, enter the verification code.\n" % (permission_url))

    else:
        verification_code = raw_input('Please log in and/or grant access via your browser at %s '
                  'then enter the verification code.' % (permission_url))


    #request access and refresh token with the obtained verification code
    response = get_authorization_tokens(verification_code)

    LOG.critical("Response %s" % (response))

    return (final_token.key, final_token.secret, "normal")

def get_oauth_tok_sec(email, use_webbrowser = False, debug=False):
    '''
       Generate token and secret
    '''
    
    scopes = ['https://mail.google.com/', # IMAP/SMTP client access
              'https://www.googleapis.com/auth/userinfo#email'] # Email address access (verify token authorized by correct account
    
    gdata_serv = gdata.service.GDataService()
    gdata_serv.debug = debug
    gdata_serv.source = 'gmvault '
    
    gdata_serv.SetOAuthInputParameters(gdata.auth.OAuthSignatureMethod.HMAC_SHA1, \
                                       consumer_key = 'anonymous', consumer_secret = 'anonymous')
    
    params = {'xoauth_displayname':'Gmvault - Backup your Gmail account'}
    try:
        request_token = gdata_serv.FetchOAuthRequestToken(scopes=scopes, extra_parameters = params)
    except gdata.service.FetchingOAuthRequestTokenFailed, err:
        if str(err).find('Timestamp') != -1:
            LOG.critical('Is your system clock up to date? See the FAQ http://code.google.com/p/googlecl/wiki/FAQ'\
                         '#Timestamp_too_far_from_current_time\n')
            
        LOG.critical("Received Error: %s.\n" % (err) )
        LOG.critical("=== Exception traceback ===")
        LOG.critical(gmvault_utils.get_exception_traceback())
        LOG.critical("=== End of Exception traceback ===\n")
            
        return (None, None)
    
    url_params = {}
    domain = email[email.find('@')+1:]
    if domain.lower() != 'gmail.com' and domain.lower() != 'googlemail.com':
        url_params = {'hd': domain}
    
    auth_url = gdata_serv.GenerateOAuthAuthorizationURL(request_token=request_token, extra_params=url_params)
    
    #message to indicate that a browser will be opened
    raw_input('gmvault will now open a web browser page in order for you to grant gmvault access to your Gmail.\n'\
              'Please make sure you\'re logged into the correct Gmail account (%s) before granting access.\n'\
              'Press ENTER to open the browser. Once you\'ve granted access you can switch back to gmvault.' % (email))
    
    # run web browser otherwise print message with url
    if use_webbrowser:
        try:
            webbrowser.open(str(auth_url))  
        except Exception, err: #pylint: disable-msg=W0703
            LOG.critical("Error: %s.\n" % (err) )
            LOG.critical("=== Exception traceback ===")
            LOG.critical(gmvault_utils.get_exception_traceback())
            LOG.critical("=== End of Exception traceback ===\n")
        
        raw_input("You should now see the web page on your browser now.\n"\
                  "If you don\'t, you can manually open:\n\n%s\n\nOnce you've granted"\
                  " gmvault access, press the Enter key.\n" % (auth_url))
        
    else:
        raw_input('Please log in and/or grant access via your browser at %s '
                  'then hit enter.' % (auth_url))
    
    try:
        final_token = gdata_serv.UpgradeToOAuthAccessToken(request_token)
    except gdata.service.TokenUpgradeFailed:
        LOG.critical('Token upgrade failed! Could not get OAuth access token.\n Did you grant gmvault access in your browser ?')
        LOG.critical("=== Exception traceback ===")
        LOG.critical(gmvault_utils.get_exception_traceback())
        LOG.critical("=== End of Exception traceback ===\n")
        
        return (None, None)

    return (final_token.key, final_token.secret, "normal")

def generate_xoauth_req(a_token, a_secret, email, type):
    """
       generate the xoauth req from a user token and secret.
       Handle two_legged xoauth for admins.
    """
    nonce = str(random.randrange(2**64 - 1))
    timestamp = str(int(time.time()))
    if type == "two_legged": #2 legged oauth
        request = atom.http_core.HttpRequest('https://mail.google.com/mail/b/%s/imap/?xoauth_requestor_id=%s' \
                                             % (email, urllib.quote(email)), 'GET')
         
        signature = gdata.gauth.generate_hmac_signature(http_request=request, consumer_key=a_token, consumer_secret=a_secret, \
                                                        timestamp=timestamp, nonce=nonce, version='1.0', next=None)
        return '''GET https://mail.google.com/mail/b/%s/imap/?xoauth_requestor_id=%s oauth_consumer_key="%s",oauth_nonce="%s"'''\
               ''',oauth_signature="%s",oauth_signature_method="HMAC-SHA1",oauth_timestamp="%s",oauth_version="1.0"''' \
               % (email, urllib.quote(email), a_token, nonce, urllib.quote(signature), timestamp)
    else:
        request = atom.http_core.HttpRequest('https://mail.google.com/mail/b/%s/imap/' % email, 'GET')
        signature = gdata.gauth.generate_hmac_signature(
            http_request=request, consumer_key='anonymous', consumer_secret='anonymous', timestamp=timestamp,
            nonce=nonce, version='1.0', next=None, token = a_token, token_secret= a_secret)
        return '''GET https://mail.google.com/mail/b/%s/imap/ oauth_consumer_key="anonymous",oauth_nonce="%s"'''\
               ''',oauth_signature="%s",oauth_signature_method="HMAC-SHA1",oauth_timestamp="%s",oauth_token="%s"'''\
               ''',oauth_version="1.0"''' \
               % (email, nonce, urllib.quote(signature), timestamp, urllib.quote(a_token))




class CredentialHelper(object):
    """
       Helper handling all credentials
    """
    SECRET_FILEPATH = '%s/token.sec' 
    
    @classmethod
    def get_secret_key(cls, a_filepath):
        """
           Get secret key if it is in the file otherwise generate it and save it
        """
        if os.path.exists(a_filepath):
            with open(a_filepath).read() as f:
                secret = f.read()
        else:
            secret = gmvault_utils.make_password()

            fdesc = os.open(a_filepath, os.O_CREAT|os.O_WRONLY, 0600)
            try:
                the_bytes = os.write(fdesc, secret)
            finally:
                os.close(fdesc) #close anyway

            if the_bytes < len(secret):
                raise Exception("Error: Cannot write secret in %s" % a_filepath)

        return secret
    
    @classmethod
    def store_passwd(cls, email, passwd):
        """
           Encrypt and store gmail password
        """
        passwd_file = '%s/%s.passwd' % (gmvault_utils.get_home_dir_path(), email)
    
        fdesc = os.open(passwd_file, os.O_CREAT|os.O_WRONLY, 0600)
        
        cipher       = blowfish.Blowfish(cls.get_secret_key(cls.SECRET_FILEPATH % (gmvault_utils.get_home_dir_path())))
        cipher.initCTR()
    
        encrypted = cipher.encryptCTR(passwd)
        the_bytes = os.write(fdesc, encrypted)
    
        os.close(fdesc)
        
        if the_bytes < len(encrypted):
            raise Exception("Error: Cannot write password in %s" % (passwd_file))
        
    @classmethod
    def store_oauth_credentials(cls, email, token, secret, type):
        """
           store oauth_credentials
        """
        oauth_file = '%s/%s.oauth' % (gmvault_utils.get_home_dir_path(), email)
    
        fdesc = os.open(oauth_file, os.O_CREAT|os.O_WRONLY, 0600)
        
        os.write(fdesc, token)
        os.write(fdesc, '::')
        os.write(fdesc, secret)
        os.write(fdesc, '::')
        os.write(fdesc, type)
    
        os.close(fdesc)
    
    @classmethod
    def read_password(cls, email):
        """
           Read password credentials
           Look by default to ~/.gmvault
           Look for file ~/.gmvault/email.passwd
        """
        gmv_dir = gmvault_utils.get_home_dir_path()

        #look for email.passwed in GMV_DIR
        user_passwd_file_path = "%s/%s.passwd" % (gmv_dir, email)

        password = None
        if os.path.exists(user_passwd_file_path):
            with open(user_passwd_file_path) as f:
                password = f.read()
            cipher       = blowfish.Blowfish(cls.get_secret_key(cls.SECRET_FILEPATH % (gmvault_utils.get_home_dir_path())))
            cipher.initCTR()
            password     = cipher.decryptCTR(password)

        return password

    @classmethod
    def read_oauth_tok_sec(cls, email):
        """
           Read oauth token secret credential
           Look by default to ~/.gmvault
           Look for file ~/.gmvault/email.oauth
        """
        gmv_dir = gmvault_utils.get_home_dir_path()
        
        #look for email.passwed in GMV_DIR
        user_oauth_file_path = "%s/%s.oauth" % (gmv_dir, email)

        token  = None
        secret = None
        type   = None
        if os.path.exists(user_oauth_file_path):
            LOG.critical("Get XOAuth credential from %s.\n" % user_oauth_file_path)

            try:
                with open(user_oauth_file_path) as oauth_file:
                    oauth_result = oauth_file.read()
                if oauth_result:
                    oauth_result = oauth_result.split('::')
                    if len(oauth_result) == 2:
                        token  = oauth_result[0]
                        secret = oauth_result[1]
                        type   = "normal"
                    elif len(oauth_result) == 3:
                        token  = oauth_result[0]
                        secret = oauth_result[1]
                        type   = oauth_result[2]
            except Exception, _: #pylint: disable-msg=W0703              
                LOG.critical("Cannot read oauth credentials from %s. Force oauth credentials renewal." % user_oauth_file_path)
                LOG.critical("=== Exception traceback ===")
                LOG.critical(gmvault_utils.get_exception_traceback())
                LOG.critical("=== End of Exception traceback ===\n")

        if token: token   = token.strip() #pylint: disable-msg=C0321
        if secret: secret = secret.strip()  #pylint: disable-msg=C0321
        if type: type = type.strip()

        return token, secret, type

    @classmethod
    def read_oauth2_tok_sec(cls, email):
        """
           Read oauth token secret credential
           Look by default to ~/.gmvault
           Look for file ~/.gmvault/email.oauth2
        """
        gmv_dir = gmvault_utils.get_home_dir_path()

        #look for email.passwed in GMV_DIR
        user_oauth_file_path = "%s/%s.oauth2" % (gmv_dir, email)

        token  = None
        secret = None
        type   = None
        if os.path.exists(user_oauth_file_path):
            LOG.critical("Get OAuth2 credential from %s.\n" % user_oauth_file_path)

            try:
                with open(user_oauth_file_path) as oauth_file:
                    oauth_result = oauth_file.read()
                if oauth_result:
                    oauth_result = oauth_result.split('::')
                    if len(oauth_result) == 2:
                        token  = oauth_result[0]
                        secret = oauth_result[1]
                        type   = "normal"
                    elif len(oauth_result) == 3:
                        token  = oauth_result[0]
                        secret = oauth_result[1]
                        type   = oauth_result[2]
            except Exception, _: #pylint: disable-msg=W0703
                LOG.critical("Cannot read oauth credentials from %s. Force oauth credentials renewal." % user_oauth_file_path)
                LOG.critical("=== Exception traceback ===")
                LOG.critical(gmvault_utils.get_exception_traceback())
                LOG.critical("=== End of Exception traceback ===\n")

        if token: token   = token.strip() #pylint: disable-msg=C0321
        if secret: secret = secret.strip()  #pylint: disable-msg=C0321
        if type: type = type.strip()

        return token, secret, type

    @classmethod
    def get_credential(cls, args, test_mode={'activate': False, 'value': 'test_password'}): #pylint: disable-msg=W0102
        """
           Deal with the credentials.
           1) Password
           --passwd passed. If --passwd passed and not password given if no password saved go in interactive mode
           2) XOAuth Token
        """
        credential = {}

        #first check that there is an email
        if not args.get('email', None):
            raise Exception("No email passed, Need to pass an email")
        
        if args['passwd'] in ['empty', 'store', 'renew']: 
            # --passwd is here so look if there is a passwd in conf file 
            # or go in interactive mode
            
            LOG.critical("Authentication performed with Gmail password.\n")
            
            passwd = cls.read_password(args['email'])
            
            #password to be renewed so need an interactive phase to get the new pass
            if not passwd or args['passwd'] in ['renew', 'store']: # go to interactive mode
                if not test_mode.get('activate', False):
                    passwd = getpass.getpass('Please enter gmail password for %s and press ENTER:' % (args['email']))
                else:
                    passwd = test_mode.get('value', 'no_password_given')
                    
                credential = { 'type' : 'passwd', 'value' : passwd}
                
                #store it in dir if asked for --store-passwd or --renew-passwd
                if args['passwd'] in ['renew', 'store']:
                    LOG.critical("Store password for %s in $HOME/.gmvault." % (args['email']))
                    cls.store_passwd(args['email'], passwd)
                    credential['option'] = 'saved'
            else:
                LOG.critical("Use password stored in $HOME/.gmvault dir (Storing your password here is not recommended).")
                credential = { 'type' : 'passwd', 'value' : passwd, 'option':'read' }
                               
        # use oauth2
        elif args['passwd'] in ('not_seen', None) and args['oauth2'] in (None, 'empty', 'renew', 'not_seen'):
            # get token secret
            # if they are in a file then no need to call get_oauth_tok_sec
            # will have to add 2 legged 
            LOG.critical("Authentication performed with Gmail OAuth2 access token.\n")

            token, secret, type = cls.read_oauth_tok_sec(args['email'])
           
            if not token or args['oauth2'] == 'renew':
                
                if args['oauth2'] == 'renew':
                    LOG.critical("Renew OAuth2 token (normal). Initiate interactive session to get it from Gmail.\n")
                else:
                    LOG.critical("Initiate interactive session to get OAuth2 token from Gmail.\n")

                 token, secret, type = get_oauth_tok_sec(args['email'], use_webbrowser = True)
                
                if not token:
                    raise Exception("Cannot get OAuth2 token from Gmail. See Gmail error message")
                #store newly created token
                cls.store_oauth_credentials(args['email'], token, secret, type)
               
            xoauth_req = generate_xoauth_req(token, secret, args['email'], type)
            
            LOG.critical("Successfully read oauth credentials.\n")

            credential = { 'type' : 'xoauth', 'value' : xoauth_req, 'option':None }
        # use oauth1
        elif args['passwd'] in ('not_seen', None) and args['oauth'] in (None, 'empty', 'renew', 'not_seen'):
            # get token secret
            # if they are in a file then no need to call get_oauth_tok_sec
            # will have to add 2 legged
            LOG.critical("Authentication performed with Gmail XOAuth token.\n")

            two_legged = args.get('two_legged', False) # 2 legged oauth

            token, secret, type = cls.read_oauth_tok_sec(args['email'])

            if not token or args['oauth'] == 'renew':

                if args['oauth'] == 'renew':
                    LOG.critical("Renew XOAuth token (normal or 2-legged). Initiate interactive session to get it from Gmail.\n")
                else:
                    LOG.critical("Initiate interactive session to get XOAuth normal or 2-legged token from Gmail.\n")

                if two_legged:
                    token, secret, type = get_2_legged_oauth_tok_sec()
                else:
                    token, secret, type = get_oauth_tok_sec(args['email'], use_webbrowser = True)

                if not token:
                    raise Exception("Cannot get XOAuth token from Gmail. See Gmail error message")
                #store newly created token
                cls.store_oauth_credentials(args['email'], token, secret, type)

            xoauth_req = generate_xoauth_req(token, secret, args['email'], type)

            LOG.critical("Successfully read oauth credentials.\n")

            credential = { 'type' : 'xoauth', 'value' : xoauth_req, 'option':None }
                        
        return credential

    @classmethod
    def get_xoauth_req_from_email(cls, email):
        """
           This will be used to reconnect after a timeout
        """
        token, secret, type = cls.read_oauth_tok_sec(email)
        if not token: 
            raise Exception("Error cannot read token, secret from")
        
        xoauth_req = generate_xoauth_req(token, secret, email, type)
        
        return xoauth_req
