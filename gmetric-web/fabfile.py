from fabric.api import *
from fabric.contrib.files import exists

env.project_name = 'gmetric-web'

def live():
    env.hosts = ['']
    env.path = '/srv/gmetric-web'
    env.user = ''
    env.group = ''

def setup():
    """
    Setup a fresh virtualenv as well as a few useful directories, then run
    a full deployment
    """
    require('hosts')
    require('group')
    require('path')
    require('project_name')

    sudo('mkdir -p %s; chown %s:%s -R %s' % (env.path, env.user, env.group, env.path))
    run('cd %s; virtualenv .;' % env.path)
    run('cd %s; bin/easy_install pip' % env.path)
    if not exists('%s/releases' % env.path):
        run('cd %s; mkdir releases;' % env.path)
    if not exists('%s/shared' % env.path):
        run('cd %s; mkdir shared;' % env.path)
    if not exists('%s/packages' % env.path):
        run('cd %s; mkdir packages;' % env.path)


def deploy():
    """
    Deploy the latest version of the site to the servers, install any
    required third party modules, install the virtual host and 
    then restart the webserver
    """
    require('hosts')
    require('path')

    import time
    env.release = time.strftime('%Y%m%d%H%M%S')

    upload_tar_from_local()
    install_requirements()
    symlink_current_release()

def deploy_version(version):
    "Specify a specific version to be made live"
    require('hosts', provided_by=[local])
    require('path')

    env.version = version
    run('cd %s; rm releases/previous; mv releases/current releases/previous;' % env.path)
    run('cd %s; ln -s %s releases/current' % (env.path, env.version))

def rollback():
    """
    Limited rollback capability. Simple loads the previously current
    version of the code. Rolling back again will swap between the two,
    NOT keep going back in time.
    """
    require('hosts', provided_by=[local])
    require('path')

    run('cd %s; mv releases/current releases/_previous;' % env.path)
    run('cd %s; mv releases/previous releases/current;' % env.path)
    run('cd %s; mv releases/_previous releases/previous;' % env.path)
    
def upload_tar_from_local():
    require('release', provided_by=[deploy])
    "Create an archive from the current local folder"
    local('find . -name "*.pyc" -exec rm -rf {} \;')
    local("cd ../; tar -pczf %s.tar.gz --exclude '.git' --exclude '.svn' --exclude '.pyc' gmetric-web" % env.release)
    run('mkdir %s/releases/%s/' % (env.path, env.release))
    put('../%s.tar.gz' % env.release, '%s/packages/' % (env.path))
    run('cd %s/releases/%s/ && tar zxf ../../packages/%s.tar.gz' % (env.path, env.release, env.release))
    local('rm ../%s.tar.gz' % env.release)

def install_requirements():
    "Install the required packages from the requirements file using pip"
    require('release', provided_by=[deploy])
    run('cd %s; pip install -E . -r ./releases/%s/%s/requirements.txt' % (env.path, env.release, env.project_name))

def symlink_current_release():
    "Symlink our current release"
    require('release', provided_by=[deploy])
    if exists('%s/releases/previous' % env.path):
        run('rm %s/releases/previous' % env.path)
    if exists('%s/releases/current' % env.path):
        run('mv %s/releases/current %s/releases/previous' % (env.path, env.path))
    run('cd %s; ln -s %s releases/current' % (env.path, env.release))
