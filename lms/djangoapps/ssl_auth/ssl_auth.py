"""
User authentication backend for ssl (no pw required)
"""

from django.conf import settings
from django.contrib import auth
from django.contrib.auth.models import User, check_password
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.middleware import RemoteUserMiddleware
from django.core.exceptions import ImproperlyConfigured
import os, string, re
from random import choice

from student.models import UserProfile

#-----------------------------------------------------------------------------

def ssl_dn_extract_info(dn):
    '''
    Extract username, email address (may be anyuser@anydomain.com) and full name
    from the SSL DN string.  Return (user,email,fullname) if successful, and None
    otherwise.
    '''
    ss = re.search('/emailAddress=(.*)@([^/]+)',dn)
    if ss:
        user = ss.group(1)
        email = "%s@%s" % (user,ss.group(2))
    else:
        return None
    ss = re.search('/CN=([^/]+)/',dn)
    if ss:
        fullname = ss.group(1)
    else:
        return None
    return (user,email,fullname)

def check_nginx_proxy(request):
    '''
    Check for keys in the HTTP header (META) to se if we are behind an ngix reverse proxy.
    If so, get user info from the SSL DN string and return that, as (user,email,fullname)
    '''
    m = request.META
    if m.has_key('HTTP_X_REAL_IP'):	# we're behind a nginx reverse proxy, which has already done ssl auth
        if not m.has_key('HTTP_SSL_CLIENT_S_DN'):
            return None
        dn = m['HTTP_SSL_CLIENT_S_DN']
        return ssl_dn_extract_info(dn)
    return None

#-----------------------------------------------------------------------------

def get_ssl_username(request):
    x = check_nginx_proxy(request)
    if x:
        return x[0]
    env = request._req.subprocess_env
    if env.has_key('SSL_CLIENT_S_DN_Email'):
        email = env['SSL_CLIENT_S_DN_Email']
        user = email[:email.index('@')]
        return user
    return None

#-----------------------------------------------------------------------------

class NginxProxyHeaderMiddleware(RemoteUserMiddleware):
    '''
    Django "middleware" function for extracting user information from HTTP request.
    
    '''
    # this field is generated by nginx's reverse proxy
    header = 'HTTP_SSL_CLIENT_S_DN'	# specify the request.META field to use
        
    def process_request(self, request):
        # AuthenticationMiddleware is required so that request.user exists.
        if not hasattr(request, 'user'):
            raise ImproperlyConfigured(
                "The Django remote user auth middleware requires the"
                " authentication middleware to be installed.  Edit your"
                " MIDDLEWARE_CLASSES setting to insert"
                " 'django.contrib.auth.middleware.AuthenticationMiddleware'"
                " before the RemoteUserMiddleware class.")

        #raise ImproperlyConfigured('[ProxyHeaderMiddleware] request.META=%s' % repr(request.META))

        try:
            username = request.META[self.header]	# try the nginx META key first
        except KeyError:
            try:
                env = request._req.subprocess_env	# else try the direct apache2 SSL key
                if env.has_key('SSL_CLIENT_S_DN'):
                    username = env['SSL_CLIENT_S_DN']
                else:
                    raise ImproperlyConfigured('no ssl key, env=%s' % repr(env))
                    username = ''
            except:
                # If specified header doesn't exist then return (leaving
                # request.user set to AnonymousUser by the
                # AuthenticationMiddleware).
                return
        # If the user is already authenticated and that user is the user we are
        # getting passed in the headers, then the correct user is already
        # persisted in the session and we don't need to continue.

        #raise ImproperlyConfigured('[ProxyHeaderMiddleware] username=%s' % username)

        if request.user.is_authenticated():
            if request.user.username == self.clean_username(username, request):
                #raise ImproperlyConfigured('%s already authenticated (%s)' % (username,request.user.username))
                return
        # We are seeing this user for the first time in this session, attempt
        # to authenticate the user.
        #raise ImproperlyConfigured('calling auth.authenticate, remote_user=%s' % username)
        user = auth.authenticate(remote_user=username)
        if user:
            # User is valid.  Set request.user and persist user in the session
            # by logging the user in.
            request.user = user
            if settings.DEBUG: print "[ssl_auth.ssl_auth.NginxProxyHeaderMiddleware] logging in user=%s" % user
            auth.login(request, user)
            
    def clean_username(self,username,request):
        '''
        username is the SSL DN string - extract the actual username from it and return
        '''
        info = ssl_dn_extract_info(username)
        if not info:
            return None
        (username,email,fullname) = info
        return username

#-----------------------------------------------------------------------------

class SSLLoginBackend(ModelBackend):
    '''
    Django authentication back-end which auto-logs-in a user based on having
    already authenticated with an MIT certificate (SSL).
    '''
    def authenticate(self, username=None, password=None, remote_user=None):

        # remote_user is from the SSL_DN string.  It will be non-empty only when
        # the user has already passed the server authentication, which means
        # matching with the certificate authority.
        if not remote_user:	
            # no remote_user, so check username (but don't auto-create user)
            if not username:
                return None
            return None # pass on to another authenticator backend
            #raise ImproperlyConfigured("in SSLLoginBackend, username=%s, remote_user=%s" % (username,remote_user))
            try:
                user = User.objects.get(username=username)	# if user already exists don't create it
                return user
            except User.DoesNotExist:
                return None
            return None

        #raise ImproperlyConfigured("in SSLLoginBackend, username=%s, remote_user=%s" % (username,remote_user))
        #if not os.environ.has_key('HTTPS'):
        #    return None
        #if not os.environ.get('HTTPS')=='on':	# only use this back-end if HTTPS on
        #    return None

        def GenPasswd(length=8, chars=string.letters + string.digits):
            return ''.join([choice(chars) for i in range(length)])

        # convert remote_user to user, email, fullname
        info = ssl_dn_extract_info(remote_user)
        #raise ImproperlyConfigured("[SSLLoginBackend] looking up %s" % repr(info))
        if not info:
            #raise ImproperlyConfigured("[SSLLoginBackend] remote_user=%s, info=%s" % (remote_user,info))
            return None
        (username,email,fullname) = info

        try:
            user = User.objects.get(username=username)	# if user already exists don't create it
        except User.DoesNotExist:
            if not settings.DEBUG:
                raise "User does not exist. Not creating user; potential schema consistency issues"
            #raise ImproperlyConfigured("[SSLLoginBackend] creating %s" % repr(info))
            user = User(username=username, password=GenPasswd())	# create new User
            user.is_staff = False
            user.is_superuser = False
            # get first, last name from fullname
            name = fullname
            if not name.count(' '):
                user.first_name = " "
                user.last_name = name
                mn = ''
            else:
                user.first_name = name[:name.find(' ')]
                ml = name[name.find(' '):].strip()
                if ml.count(' '):
                    user.last_name = ml[ml.rfind(' '):]
                    mn = ml[:ml.rfind(' ')]
                else:
                    user.last_name = ml
                    mn = ''
            # set email
            user.email = email
            # cleanup last name
            user.last_name = user.last_name.strip()
            # save
            user.save()
            
            # auto-create user profile
            up = UserProfile(user=user)
            up.name = fullname
            up.save()

            #tui = user.get_profile()
            #tui.middle_name = mn
            #tui.role = 'Misc'
            #tui.section = None	# no section assigned at first
            #tui.save()
            # return None
        return user

    def get_user(self, user_id):
        #if not os.environ.has_key('HTTPS'):
        #    return None
        #if not os.environ.get('HTTPS')=='on':	# only use this back-end if HTTPS on
        #    return None
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
        
#-----------------------------------------------------------------------------
# OLD!

class AutoLoginBackend:
    def authenticate(self, username=None, password=None):
        raise ImproperlyConfigured("in AutoLoginBackend, username=%s" % username)
        if not os.environ.has_key('HTTPS'):
            return None
        if not os.environ.get('HTTPS')=='on':# only use this back-end if HTTPS on
            return None

        def GenPasswd(length=8, chars=string.letters + string.digits):
            return ''.join([choice(chars) for i in range(length)])

        try:
                user = User.objects.get(username=username)
        except User.DoesNotExist:
            user = User(username=username, password=GenPasswd())
            user.is_staff = False
            user.is_superuser = False
            # get first, last name 
            name = os.environ.get('SSL_CLIENT_S_DN_CN').strip()
            if not name.count(' '):
                user.first_name = " "
                user.last_name = name
                mn = ''
            else:
                user.first_name = name[:name.find(' ')]
                ml = name[name.find(' '):].strip()
                if ml.count(' '):
                    user.last_name = ml[ml.rfind(' '):]
                    mn = ml[:ml.rfind(' ')]
                else:
                    user.last_name = ml
                    mn = ''
            # get email
            user.email = os.environ.get('SSL_CLIENT_S_DN_Email')
            # save
            user.save()
            tui = user.get_profile()
            tui.middle_name = mn
            tui.role = 'Misc'
            tui.section = None# no section assigned at first
            tui.save()
            # return None
            return user

    def get_user(self, user_id):
        if not os.environ.has_key('HTTPS'):
            return None
        if not os.environ.get('HTTPS')=='on':# only use this back-end if HTTPS on
            return None
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None