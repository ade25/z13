import getpass
from fabric.api import cd
from fabric.api import env
from fabric.api import local
from fabric.api import run
from fabric.api import task

from ade25.fabfiles import project
from ade25.fabfiles.server import setup
from ade25.fabfiles.server import controls
from ade25.fabfiles import hotfix as hf

from slacker import Slacker
slack = Slacker('xoxp-2440800772-2440800774-2520374751-468e84')

env.use_ssh_config = True
env.forward_agent = True
env.port = '22222'
env.user = 'root'
env.code_user = 'root'
env.prod_user = 'www'
env.webserver = '/opt/webserver/buildout.webserver'
env.code_root = '/opt/webserver/buildout.webserver'
env.host_root = '/opt/sites'

env.hosts = ['z13']
env.hosted_sites = [
    'kh',
    'kipungani',
    'zimtec',
    'retold',
    'hautnah',
    'ces',
]

env.hosted_sites_locations = [
    '/opt/sites/kh/buildout.kh',
    '/opt/zope/kipungani/',
    '/opt/zope/zimtec/',
    '/opt/zope/retold/',
    '/opt/zope/hautnah/',
    '/opt/sites/ces/buildout.ces ',
]


@task
def restart():
    """ Restart all """
    with cd(env.webserver):
        run('nice bin/supervisorctl restart all')


@task
def restart_nginx():
    """ Restart Nginx """
    controls.restart_nginx()


@task
def restart_varnish():
    """ Restart Varnish """
    controls.restart_varnish()


@task
def restart_haproxy():
    """ Restart HAProxy """
    controls.restart_haproxy()


@task
def ctl(*cmd):
    """Runs an arbitrary supervisorctl command."""
    with cd(env.webserver):
        run('nice bin/supervisorctl ' + ' '.join(cmd))


@task
def prepare_deploy():
    """ Push committed local changes to git """
    local('git push')


@task
def deploy_site():
    """ Deploy a new site to production """
    controls.update()
    controls.build()
    controls.reload_supervisor()


@task
def deploy(actor=None):
    """ Deploy current master to production server """
    opts = dict(
        actor=actor or env.get('actor') or getpass.getuser(),
    )
    project.site.update()
    project.site.build()
    with cd(env.webserver):
        run('bin/supervisorctl reread')
        run('bin/supervisorctl update')
    msg = '[z13] z13.ade25.de server configuration deployed by %(actor)s' % opts
    user = 'fabric'
    icon = ':shipit:'
    slack.chat.post_message('#general', msg, username=user, icon_emoji=icon)


@task
def update(sitename=None, actor=None):
    """ Deploy changes to a hosted site """
    opts = dict(
        sitename=sitename,
        actor=actor or env.get('actor') or getpass.getuser(),
    )
    path = '{0}/{1}/buildout.{2}'.format(env.host_root, sitename, sitename)
    with cd(path):
        run('nice git pull')
        run('nice bin/buildout -Nc deployment.cfg')
    with cd(env.webserver):
        run('nice bin/supervisorctl restart instance-%(sitename)s' % opts)
    msg = '[z13] %(sitename)s deployed by %(actor)s' % opts
    user = 'fabric'
    icon = ':shipit:'
    slack.chat.post_message('#general', msg, username=user, icon_emoji=icon)


@task
def hotfix(addon=None):
    """ Apply hotfix to all hosted sites """
    hf.prepare_sites()
    hf.process_hotfix()


def initialize_server():
    """ Initialize new server (should normally only run once) """
    setup.install_system_libs()
    setup.set_project_user_and_group('www', 'www')
