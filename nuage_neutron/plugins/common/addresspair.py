# Copyright 2015 Alcatel-Lucent USA Inc.
#
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
import six

from oslo_log import log as logging
from oslo_utils import excutils

from neutron.callbacks import resources
from neutron.extensions import allowedaddresspairs as addr_pair
from neutron.extensions import portbindings
from neutron.extensions import portsecurity
from neutron_lib import constants as lib_constants
from neutron_lib.plugins import directory

from nuage_neutron.plugins.common.base_plugin import BaseNuagePlugin
from nuage_neutron.plugins.common import constants
from nuage_neutron.plugins.common.exceptions import SubnetMappingNotFound
from nuage_neutron.plugins.common import nuagedb

LOG = logging.getLogger(__name__)


class NuageAddressPair(BaseNuagePlugin):

    def register(self):
        self.nuage_callbacks.subscribe(self.post_port_update_addresspair,
                                       resources.PORT, constants.AFTER_UPDATE)
        self.nuage_callbacks.subscribe(self.post_port_create_addresspair,
                                       resources.PORT, constants.AFTER_CREATE)
        self.nuage_callbacks.subscribe(
            self.post_router_interface_create_addresspair,
            resources.ROUTER_INTERFACE,
            constants.AFTER_CREATE)
        self.nuage_callbacks.subscribe(
            self.post_router_interface_delete_addresspair,
            resources.ROUTER_INTERFACE,
            constants.AFTER_DELETE)

    @property
    def core_plugin(self):
        if not getattr(self, '_core_plugin', None):
            self._core_plugin = directory.get_plugin()
        return self._core_plugin

    @property
    def l3_plugin(self):
        if not getattr(self, '_l3_plugin', None):
            self._l3_plugin = directory.get_plugin(lib_constants.L3)
        return self._l3_plugin

    def _make_fip_dict_with_subnet_id(self, fip):
        fip_dict = self.l3_plugin._make_floatingip_dict(fip)
        fip_dict['fip_subnet_id'] = fip.port.fixed_ips[0].subnet_id
        return fip_dict

    def _create_vips(self, context, subnet_mapping, port, nuage_vport):
        port_vip_dict = nuage_vip_dict = dict()
        enable_spoofing = False
        vsd_subnet = self._find_vsd_subnet(context, subnet_mapping)
        fips_per_vip = nuagedb.get_floatingip_per_vip_in_network(
            context.session, port['network_id'], self.get_device_owners_vip())
        fips_per_vip = {vip: self._make_fip_dict_with_subnet_id(fip)
                        for vip, fip in six.iteritems(fips_per_vip)}

        if (port.get(constants.VIPS_FOR_PORT_IPS) and
                self._is_l3(subnet_mapping)):
            for vip_ip in port.get(constants.VIPS_FOR_PORT_IPS):
                params = {
                    'vip': vip_ip,
                    'mac': port['mac_address'],
                    'subnet_id': subnet_mapping['nuage_subnet_id'],
                    'vsd_subnet': vsd_subnet,
                    'vport_id': nuage_vport['ID'],
                    'port_ips': [],
                    'port_mac': '',
                    'externalID': port['id'],
                    'os_fip': None,
                    'vsd_l3domain_id': None
                }
                try:
                    enable_spoofing |= self.vsdclient.create_vip(params)
                    port_vip_dict[params['vip']] = params['mac']
                except Exception as e:
                    if not self._get_port_from_neutron(context, port):
                        return
                    with excutils.save_and_reraise_exception():
                        LOG.error(
                            "Error in creating vip for ip %(vip)s and mac "
                            "%(mac)s: %(err)s", {'vip': vip_ip,
                                                 'mac': port['mac_address'],
                                                 'err': e.message})
                        self.vsdclient.delete_vips(nuage_vport['ID'],
                                                   port_vip_dict,
                                                   port_vip_dict.keys())

        for allowed_addr_pair in port[addr_pair.ADDRESS_PAIRS]:
            vip = allowed_addr_pair['ip_address']
            mac = allowed_addr_pair['mac_address']

            os_fip = fips_per_vip.get(vip)
            if os_fip:
                vsd_l3domain_id = nuagedb.get_ent_rtr_mapping_by_rtrid(
                    context.session,
                    os_fip['router_id'])['nuage_router_id']
            else:
                vsd_l3domain_id = None

            params = {
                'vip': vip,
                'mac': mac,
                'subnet_id': subnet_mapping['nuage_subnet_id'],
                'vsd_subnet': vsd_subnet,
                'vport_id': nuage_vport['ID'],
                'port_ips': [ip['ip_address'] for ip in port['fixed_ips']],
                'port_mac': port['mac_address'],
                'externalID': port['id'],
                'os_fip': os_fip,
                'vsd_l3domain_id': vsd_l3domain_id
            }

            try:
                enable_spoofing |= self.vsdclient.create_vip(params)
                nuage_vip_dict[params['vip']] = params['mac']
            except Exception as e:
                if not self._get_port_from_neutron(context, port):
                    return
                with excutils.save_and_reraise_exception():
                    LOG.error("Error in creating vip for ip %(vip)s and mac "
                              "%(mac)s: %(err)s", {'vip': vip,
                                                   'mac': mac,
                                                   'err': e.message})
                    self.vsdclient.delete_vips(nuage_vport['ID'],
                                               nuage_vip_dict,
                                               nuage_vip_dict.keys())
        if port[portsecurity.PORTSECURITY] is not False:
            try:
                self.vsdclient.update_mac_spoofing_on_vport(
                    nuage_vport['ID'],
                    constants.ENABLED if enable_spoofing else
                    constants.INHERITED)
            except Exception:
                if not self._get_port_from_neutron(context, port):
                    return
                raise

    def _update_vips(self, context, subnet_mapping, port, nuage_vport,
                     deleted_addr_pairs):
        if deleted_addr_pairs:
            # If some addr pairs were deleted we might have to undo some
            # action on VSD
            for addrpair in deleted_addr_pairs:
                params = {
                    'vip': addrpair['ip_address'],
                    'mac': addrpair['mac_address'],
                    'subnet_id': subnet_mapping['nuage_subnet_id'],
                    'vport_id': nuage_vport['ID'],
                    'port_ips': [ip['ip_address'] for ip in port['fixed_ips']],
                    'port_mac': port['mac_address'],
                    'subnet_mapping': subnet_mapping
                }
                self.vsdclient.process_deleted_addr_pair(params)

        # Get all the vips on vport
        nuage_vips = self.vsdclient.get_vips(nuage_vport['ID'])

        nuage_vip_dict = dict()
        for nuage_vip in nuage_vips:
            nuage_vip_dict[nuage_vip['vip']] = nuage_vip['mac']

        os_vip_dict = dict()
        vip_for_ip_dict = dict()
        if addr_pair.ADDRESS_PAIRS in port:
            for allowed_addr_pair in port[addr_pair.ADDRESS_PAIRS]:
                # OS allows addr pairs with same ip and different mac,
                # which does not make sense in VSD. We will create only one
                # of the pair in VSD
                if allowed_addr_pair['ip_address'] in os_vip_dict:
                    LOG.warning("Duplicate ip found in allowed address "
                                "pairs, so %s will be ignored",
                                allowed_addr_pair)
                    continue
                os_vip_dict[allowed_addr_pair['ip_address']] = (
                    allowed_addr_pair['mac_address'])
                vip_for_ip_dict[allowed_addr_pair['ip_address']] = (
                    allowed_addr_pair['mac_address'])
        port_ip_vip_add_list = []
        if port.get(constants.VIPS_FOR_PORT_IPS):
            for vip in port.get(constants.VIPS_FOR_PORT_IPS):
                if vip not in nuage_vip_dict:
                    port_ip_vip_add_list.append(vip)
                elif port['mac_address'] != nuage_vip_dict[vip]:
                    port_ip_vip_add_list.append(vip)
                else:
                    os_vip_dict[vip] = port['mac_address']

        vips_add_list = []
        vips_delete_set = set()
        for vip, mac in os_vip_dict.iteritems():
            if vip in nuage_vip_dict:
                # Check if mac is same
                if (mac != nuage_vip_dict.get(vip) or
                        (vip in port.get(constants.VIPS_FOR_PORT_IPS) and
                         mac != port['mac_address'])):
                    vips_add_dict = {
                        'ip_address': vip,
                        'mac_address': mac
                    }
                    vips_add_list.append(vips_add_dict)
            else:
                vips_add_dict = {
                    'ip_address': vip,
                    'mac_address': mac
                }
                vips_add_list.append(vips_add_dict)

        for vip, mac in nuage_vip_dict.iteritems():
            if vip in os_vip_dict:
                # Check if mac is same
                if (mac != os_vip_dict.get(vip) or
                        (vip in port.get(constants.VIPS_FOR_PORT_IPS) and
                         mac != port['mac_address'])):
                    vips_delete_set.add(vip)
            else:
                vips_delete_set.add(vip)

        if vips_delete_set:
            try:
                self.vsdclient.delete_vips(nuage_vport['ID'],
                                           nuage_vip_dict,
                                           vips_delete_set)
            except Exception as e:
                with excutils.save_and_reraise_exception:
                    LOG.error("Error in deleting vips on vport %(port)s: %("
                              "err)s", {'port': nuage_vport['ID'],
                                        'err': e})
        need_vips_for_ips = True if (
            self._is_l3(subnet_mapping) and
            port.get(constants.VIPS_FOR_PORT_IPS)) else False
        if vips_add_list or need_vips_for_ips:
            port_dict = {
                addr_pair.ADDRESS_PAIRS: vips_add_list,
                'fixed_ips': port['fixed_ips'],
                'mac_address': port['mac_address'],
                'id': port['id'],
                'network_id': port['network_id'],
                constants.VIPS_FOR_PORT_IPS: port_ip_vip_add_list,
                portsecurity.PORTSECURITY: port[portsecurity.PORTSECURITY]
            }
            self._create_vips(context, subnet_mapping, port_dict, nuage_vport)

    def _process_allowed_address_pairs(self, context, port, vport,
                                       create=False, delete_addr_pairs=None):
        subnet_id = port['fixed_ips'][0]['subnet_id']
        subnet_mapping = nuagedb.get_subnet_l2dom_by_id(context.session,
                                                        subnet_id)
        if subnet_mapping:
            if vport:
                if create:
                    self._create_vips(context, subnet_mapping, port, vport)
                else:
                    self._update_vips(context, subnet_mapping,
                                      port, vport, delete_addr_pairs)

    @staticmethod
    def _verify_allowed_address_pairs(port, original_port):
        if (port.get(addr_pair.ADDRESS_PAIRS) ==
                original_port.get(addr_pair.ADDRESS_PAIRS) and
                original_port.get(constants.VIPS_FOR_PORT_IPS) ==
                port.get(constants.VIPS_FOR_PORT_IPS)):
            LOG.info('No allowed address pairs update required for port %s',
                     port['id'])
            return False
        return True

    def create_allowed_address_pairs(self, context, port, vport):
        self._process_allowed_address_pairs(context, port, vport, True)

    def update_allowed_address_pairs(self, context, port, original_port,
                                     vport):
        verify = self._verify_allowed_address_pairs(port, original_port)
        if not verify:
            return

        old_addr_pairs = original_port[addr_pair.ADDRESS_PAIRS]
        new_addr_pairs = port[addr_pair.ADDRESS_PAIRS]
        delete_addr_pairs = self._get_deleted_addr_pairs(old_addr_pairs,
                                                         new_addr_pairs,
                                                         port)
        self._get_deleted_vips_for_port_ips(delete_addr_pairs,
                                            original_port, port)
        self._process_allowed_address_pairs(context, port, vport,
                                            False, delete_addr_pairs)

    def _get_deleted_addr_pairs(self, old_addr_pairs, new_addr_pairs,
                                new_port):
        addr_pair_dict = dict()
        deleted_addr_pairs = []
        for addrpair in new_addr_pairs:
            addr_pair_dict[addrpair['ip_address']] = addrpair['mac_address']

        if new_port.get(constants.VIPS_FOR_PORT_IPS):
            for vip in new_port.get(constants.VIPS_FOR_PORT_IPS):
                addr_pair_dict[vip] = new_port['mac_address']

        for addrpair in old_addr_pairs:
            if addrpair['ip_address'] in addr_pair_dict:
                # check if mac is also same, if not add it to deleted list
                if (addr_pair_dict[addrpair['ip_address']] !=
                        addrpair['mac_address']):
                    deleted_addr_pairs.append(addrpair)
            else:
                deleted_addr_pairs.append(addrpair)

        return deleted_addr_pairs

    @staticmethod
    def _get_deleted_vips_for_port_ips(deleted_addr_pairs,
                                       old_port, new_port):
        if old_port.get(constants.VIPS_FOR_PORT_IPS):
            for vip in old_port.get(constants.VIPS_FOR_PORT_IPS):
                if vip not in new_port.get(constants.VIPS_FOR_PORT_IPS):
                    deleted_addr_pairs.append(
                        {'ip_address': vip,
                         'mac_address': new_port['mac_address']})
        return deleted_addr_pairs

    def process_address_pairs_of_subnet(self, context, subnet_mapping,
                                        subnet_type):
        subnet_id = subnet_mapping.subnet_id
        vsd_subnet_id = subnet_mapping.nuage_subnet_id

        filters = {'fixed_ips': {'subnet_id': [subnet_id]}}
        ports = self.core_plugin.get_ports(context,
                                           filters=filters)
        vports = self.vsdclient.get_vports(subnet_type,
                                           vsd_subnet_id)
        vports_by_port_id = dict([(vport['externalID'].split('@')[0], vport)
                                  for vport in vports])

        for port in ports:
            vport = vports_by_port_id.get(port['id'])
            LOG.debug("Process address pairs for port: %s", port)
            if vport:
                self.calculate_vips_for_port_ips(context,
                                                 port)
                self.create_allowed_address_pairs(context, port, vport)

    def post_port_create_addresspair(self, resource, event, plugin, **kwargs):
        port = kwargs.get('port')
        vport = kwargs.get('vport')
        context = kwargs.get('context')
        configure_vips = (port.get(constants.VIPS_FOR_PORT_IPS) or
                          port.get("allowed_address_pairs"))
        if (port[portbindings.VNIC_TYPE] != portbindings.VNIC_NORMAL or
                not configure_vips):
            # If there are no allowed_address_pair in the request
            # port_security_enabled False and allowed address pairs are
            # mutually exclusive in Neutron
            return

        try:
            nuagedb.get_subnet_l2dom_by_port_id(context.session, port['id'])
            self.create_allowed_address_pairs(context, port, vport)
        except SubnetMappingNotFound:
            pass

    def post_port_update_addresspair(self, resource, event, plugin, context,
                                     port, original_port, vport, rollbacks,
                                     **kwargs):
        if port[portbindings.VNIC_TYPE] != portbindings.VNIC_NORMAL:
            return

        self.update_allowed_address_pairs(context, port, original_port, vport)
        rollbacks.append((self.update_allowed_address_pairs,
                          [context, original_port, port, vport], {}))

    def post_router_interface_create_addresspair(self, resource, event, plugin,
                                                 **kwargs):
        context = kwargs['context']
        subnet_mapping = kwargs['subnet_mapping']
        self.process_address_pairs_of_subnet(context,
                                             subnet_mapping,
                                             constants.L3SUBNET)

    def post_router_interface_delete_addresspair(self, resource, event, plugin,
                                                 **kwargs):
        context = kwargs['context']
        subnet_mapping = kwargs['subnet_mapping']
        self.process_address_pairs_of_subnet(context,
                                             subnet_mapping,
                                             constants.L2DOMAIN)
