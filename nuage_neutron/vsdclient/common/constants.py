# Copyright 2016 NOKIA
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

REST_SUCCESS_CODES = range(200, 207)
DEF_OPENSTACK_USER = 'os_user'
DEF_OPENSTACK_USER_EMAIL = 'osuser@nuage-openstack.com'
REST_SERV_UNAVAILABLE_CODE = 503

VSD_RESP_OBJ = 3
CONFLICT_ERR_CODE = 409
RES_NOT_FOUND = 404
RES_EXISTS_INTERNAL_ERR_CODE = '2510'
VSD_NO_ATTR_CHANGES_TO_MODIFY_ERR_CODE = '2039'
VSD_IP_IN_USE_ERR_CODE = '2704'
VSD_PRIORITY_CONFLICT_ERR_CODE = '2591'

PROTO_NAME_TO_NUM = {
    'tcp': 6,
    'udp': 17,
    'icmp': 1
}
NUAGE_ACL_INGRESS = 'ingress'
NUAGE_ACL_EGRESS = 'egress'
NUAGE_ACL_INGRESS_TEMPLATE = 'ingressacltemplate'
NUAGE_ACL_EGRESS_TEMPLATE = 'egressacltemplate'
NUAGE_DEFAULT_L2_INGRESS_ACL = '_def_ibl2acl'
NUAGE_DEFAULT_L2_EGRESS_ACL = '_def_obl2acl'
NUAGE_DEFAULT_L3_INGRESS_ACL = '_def_ibl3acl'
NUAGE_DEFAULT_L3_EGRESS_ACL = '_def_obl3acl'

DHCP_OPTIONS = {
    'gateway_ip': '03',
    'dns_nameservers': '06',
    'classless-static-route': '79',  # 121
    'microsoft-classless-static-route': 'f9'  # 249
}
DHCP_ROUTER_OPTION = '03'

PRCS_DHCP_OPT_AS_RAW_HEX = [46, 77, 94, 97, 121, 125, 255]

NOVA_PORT_OWNER_PREF = 'compute:'

DEF_NUAGE_ZONE_PREFIX = 'def_zone'
DEF_L3DOM_TEMPLATE_PFIX = '_def_L3_Template'
DEF_L2DOM_TEMPLATE_PFIX = '_def_L2_Template'
TEMPLATE_ISOLATED_ZONE = 'openstack-isolated'
TEMPLATE_SHARED_ZONE = 'openstack-shared'

NUAGE_NOTSUPPORTED_ETHERTYPE = ['IPv6']
NUAGE_NOTSUPPORTED_ACL_MATCH = ['ethertype value IPv6']
NOT_SUPPORTED_ACL_ATTR_MSG = (','.join(NUAGE_NOTSUPPORTED_ACL_MATCH) +
                              " attribute(s) not supported by nuage plugin")
NUAGE_ACL_PROTOCOL_ANY_MAPPING = ['tcp', 'udp']
RES_POLICYGROUPS = 'policygroups'

AUDIT_LOG_DIRECTORY = '/nuageaudit'
AUDIT_LOG_FILENAME = '/audit.log'

HEX_ELEM = '[0-9A-Fa-f]'
UUID_PATTERN = '-'.join([HEX_ELEM + '{8}', HEX_ELEM + '{4}',
                         HEX_ELEM + '{4}', HEX_ELEM + '{4}',
                         HEX_ELEM + '{12}'])

NETWORK_TYPE_L2 = 'l2'
NETWORK_TYPE_L3 = 'l3'

NUAGE_PAT_DEF_ENABLED = 'default_enabled'
NUAGE_PAT_DEF_DISABLED = 'default_disabled'

ENTERPRISE = 'enterprise'
ENABLED = 'ENABLED'
DISABLED = 'DISABLED'
INHERITED = 'INHERITED'
BRIDGE_VPORT_TYPE = 'BRIDGE'
HOST_VPORT_TYPE = 'HOST'
L2DOMAIN = 'l2domain'
SUBNET = 'subnet'
ASSIGN_VLAN = 'assign'
UNASSIGN_VLAN = 'unassign'
SOFTWARE = 'SOFTWARE'
HARDWARE = 'HARDWARE'
VPORT = 'VPORT'
GW_TYPE = {
    'VSG': 'VSG',
    'VSA': 'VSA',
    'VRSG': 'VRSG'
}
VSD_TUNNEL_TYPES = {
    'VXLAN': 'VXLAN',
    'GRE': 'GRE',
    'DEFAULT': 'DC_DEFAULT'
}

HEX_ELEM = '[0-9A-Fa-f]'
UUID_PATTERN = '-'.join([HEX_ELEM + '{8}', HEX_ELEM + '{4}',
                         HEX_ELEM + '{4}', HEX_ELEM + '{4}',
                         HEX_ELEM + '{12}'])
INFINITY = 'INFINITY'

TIER_STANDARD = 'STANDARD'
TIER_NETWORK_MACRO = 'NETWORK_MACRO'
TIER_APPLICATION = 'APPLICATION'
TIER_APPLICATION_EXTENDED_NETWORK = 'APPLICATION_EXTENDED_NETWORK'

NUAGE_LDAP_MODE = 'CMS'

NUAGE_PLCY_GRP_FOR_SPOOFING = 'PG_FOR_LESS_SECURITY'
PORTSECURITY = 'port_security_enabled'

NUAGE_PERMISSION_USE = 'USE'
NUAGE_PERMISSION_READ = 'READ'
NUAGE_PERMISSION_ALL = 'ALL'
NUAGE_PERMISSION_EXTEND = 'EXTEND'
NUAGE_PERMISSION_DEPLOY = 'DEPLOY'
NUAGE_PERMISSION_INSTANTIATE = 'INSTANTIATE'
