#!/usr/bin/python
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#

"""
Sample script to exercize brick's extend_volume.

Sample script that finds an attached volume in Cinder, and then calls
brick to extend_volume.

"""
import sys

from cinderclient import client as cinder
from oslo_config import cfg
from oslo_log import log
from oslo_utils import netutils

from hpe_os_tools import auth_args
from hpe_os_tools import utils
from os_brick.initiator import connector

parser = auth_args.parser
parser.add_argument("-l", "--list",
                    help="List available attached volumes",
                    default=False, action="store_true")
parser.add_argument("-v", "--volume",
                    metavar="<cinder-volume-id>",
                    help='Cinder volume id to test for resize')


CONF = cfg.CONF
log.register_options(CONF)
CONF([], project='brick', version='1.0')
log.setup(CONF, 'brick')
LOG = log.getLogger(__name__)


def get_initiator():
    """Get the initiator connector dict."""
    # Get the intiator side connector properties
    my_ip = netutils.get_my_ipv4()
    initiator = connector.get_connector_properties('sudo', my_ip, True, False)
    LOG.debug("initiator = %s", initiator)
    return initiator


def build_cinder(args):
    """Build the cinder client object."""
    (os_username, os_password, os_tenant_name,
     os_auth_url, os_tenant_id) = (
        args.os_username, args.os_password, args.os_tenant_name,
        args.os_auth_url, args.os_tenant_id)

    # force this to version 2.0 of Cinder API
    api_version = 2

    c = cinder.Client(api_version,
                      os_username, os_password,
                      os_tenant_name,
                      os_auth_url,
                      tenant_id=os_tenant_id)
    return c


def main():
    """The main."""
    args = parser.parse_args()
    initiator = get_initiator()
    client = build_cinder(args)

    volumes = client.volumes.list(True)
    if args.list:
        for vol in volumes:
            if vol.status == 'in-use':
                print("Name: '%(name)s' %(id)s Size:%(size)sG Type:%(type)s " %
                      {'name': vol.name, 'id': vol.id, 'size': vol.size,
                       'type': vol.volume_type})

        sys.exit(0)

    info = dict()
    volume = client.volumes.get(args.volume)
    info.update(volume._info)
    info.pop('links', None)

    # now fetch the volume paths
    if volume.status == 'in-use':
        conn = client.volumes.initialize_connection(volume, initiator)
        b = connector.InitiatorConnector.factory(
            conn['driver_volume_type'], 'sudo',
            use_multipath=initiator['multipath'])
        info['system-paths'] = b.get_volume_paths(conn['data'])

    utils.print_dict(info)


if __name__ == "__main__":
    main()
