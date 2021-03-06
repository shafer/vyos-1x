# Copyright 2020 VyOS maintainers and contributors <maintainers@vyos.io>
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library.  If not, see <http://www.gnu.org/licenses/>.

# The sole purpose of this module is to hold common functions used in
# all kinds of implementations to verify the CLI configuration.
# It is started by migrating the interfaces to the new get_config_dict()
# approach which will lead to a lot of code that can be reused.

# NOTE: imports should be as local as possible to the function which
# makes use of it!

from vyos import ConfigError
from vyos.util import dict_search

def verify_mtu(config):
    """
    Common helper function used by interface implementations to perform
    recurring validation if the specified MTU can be used by the underlaying
    hardware.
    """
    from vyos.ifconfig import Interface
    if 'mtu' in config:
        mtu = int(config['mtu'])

        tmp = Interface(config['ifname'])
        min_mtu = tmp.get_min_mtu()
        max_mtu = tmp.get_max_mtu()

        if mtu < min_mtu:
            raise ConfigError(f'Interface MTU too low, ' \
                              f'minimum supported MTU is {min_mtu}!')
        if mtu > max_mtu:
            raise ConfigError(f'Interface MTU too high, ' \
                              f'maximum supported MTU is {max_mtu}!')

def verify_mtu_ipv6(config):
    """
    Common helper function used by interface implementations to perform
    recurring validation if the specified MTU can be used when IPv6 is
    configured on the interface. IPv6 requires a 1280 bytes MTU.
    """
    from vyos.template import is_ipv6
    if 'mtu' in config:
        # IPv6 minimum required link mtu
        min_mtu = 1280
        if int(config['mtu']) < min_mtu:
            interface = config['ifname']
            error_msg = f'IPv6 address will be configured on interface "{interface}" ' \
                        f'thus the minimum MTU requirement is {min_mtu}!'

            for address in (dict_search('address', config) or []):
                if address in ['dhcpv6'] or is_ipv6(address):
                    raise ConfigError(error_msg)

            tmp = dict_search('ipv6.address', config)
            if tmp and 'no_default_link_local' not in tmp:
                raise ConfigError('link-local ' + error_msg)

            if tmp and 'autoconf' in tmp:
                raise ConfigError(error_msg)

            if tmp and 'eui64' in tmp:
                raise ConfigError(error_msg)

def verify_vrf(config):
    """
    Common helper function used by interface implementations to perform
    recurring validation of VRF configuration.
    """
    from netifaces import interfaces
    if 'vrf' in config:
        if config['vrf'] not in interfaces():
            raise ConfigError('VRF "{vrf}" does not exist'.format(**config))

        if 'is_bridge_member' in config:
            raise ConfigError(
                'Interface "{ifname}" cannot be both a member of VRF "{vrf}" '
                'and bridge "{is_bridge_member}"!'.format(**config))

def verify_tunnel(config):
    """
    This helper is used to verify the common part of the tunnel
    """
    from vyos.template import is_ipv4
    from vyos.template import is_ipv6
    
    if 'encapsulation' not in config:
        raise ConfigError('Must configure the tunnel encapsulation for '\
                          '{ifname}!'.format(**config))
    
    if 'local_ip' not in config and 'dhcp_interface' not in config:
        raise ConfigError('local-ip is mandatory for tunnel')

    if 'remote_ip' not in config and config['encapsulation'] != 'gre':
        raise ConfigError('remote-ip is mandatory for tunnel')

    if {'local_ip', 'dhcp_interface'} <= set(config):
        raise ConfigError('Can not use both local-ip and dhcp-interface')

    if config['encapsulation'] in ['ipip6', 'ip6ip6', 'ip6gre', 'ip6erspan']:
        error_ipv6 = 'Encapsulation mode requires IPv6'
        if 'local_ip' in config and not is_ipv6(config['local_ip']):
            raise ConfigError(f'{error_ipv6} local-ip')

        if 'remote_ip' in config and not is_ipv6(config['remote_ip']):
            raise ConfigError(f'{error_ipv6} remote-ip')
    else:
        error_ipv4 = 'Encapsulation mode requires IPv4'
        if 'local_ip' in config and not is_ipv4(config['local_ip']):
            raise ConfigError(f'{error_ipv4} local-ip')

        if 'remote_ip' in config and not is_ipv4(config['remote_ip']):
            raise ConfigError(f'{error_ipv4} remote-ip')

    if config['encapsulation'] in ['sit', 'gre-bridge']:
        if 'source_interface' in config:
            raise ConfigError('Option source-interface can not be used with ' \
                              'encapsulation "sit" or "gre-bridge"')
    elif config['encapsulation'] == 'gre':
        if 'local_ip' in config and is_ipv6(config['local_ip']):
            raise ConfigError('Can not use local IPv6 address is for mGRE tunnels')

def verify_eapol(config):
    """
    Common helper function used by interface implementations to perform
    recurring validation of EAPoL configuration.
    """
    if 'eapol' in config:
        if not {'cert_file', 'key_file'} <= set(config['eapol']):
            raise ConfigError('Both cert and key-file must be specified '\
                              'when using EAPoL!')

def verify_mirror(config):
    """
    Common helper function used by interface implementations to perform
    recurring validation of mirror interface configuration.

    It makes no sense to mirror traffic back at yourself!
    """
    if 'mirror' in config:
        for direction, mirror_interface in config['mirror'].items():
            if mirror_interface == config['ifname']:
                raise ConfigError(f'Can not mirror "{direction}" traffic back ' \
                                   'the originating interface!')


def verify_address(config):
    """
    Common helper function used by interface implementations to perform
    recurring validation of IP address assignment when interface is part
    of a bridge or bond.
    """
    if {'is_bridge_member', 'address'} <= set(config):
        raise ConfigError(
            'Cannot assign address to interface "{ifname}" as it is a '
            'member of bridge "{is_bridge_member}"!'.format(**config))


def verify_bridge_delete(config):
    """
    Common helper function used by interface implementations to
    perform recurring validation of IP address assignmenr
    when interface also is part of a bridge.
    """
    if 'is_bridge_member' in config:
        raise ConfigError(
            'Interface "{ifname}" cannot be deleted as it is a '
            'member of bridge "{is_bridge_member}"!'.format(**config))

def verify_interface_exists(ifname):
    """
    Common helper function used by interface implementations to perform
    recurring validation if an interface actually exists.
    """
    from netifaces import interfaces
    if ifname not in interfaces():
        raise ConfigError(f'Interface "{ifname}" does not exist!')

def verify_source_interface(config):
    """
    Common helper function used by interface implementations to
    perform recurring validation of the existence of a source-interface
    required by e.g. peth/MACvlan, MACsec ...
    """
    from netifaces import interfaces
    if 'source_interface' not in config:
        raise ConfigError('Physical source-interface required for '
                          'interface "{ifname}"'.format(**config))

    if config['source_interface'] not in interfaces():
        raise ConfigError('Specified source-interface {source_interface} does '
                          'not exist'.format(**config))

    if 'source_interface_is_bridge_member' in config:
        raise ConfigError('Invalid source-interface {source_interface}. Interface '
                          'is already a member of bridge '
                          '{source_interface_is_bridge_member}'.format(**config))

    if 'source_interface_is_bond_member' in config:
        raise ConfigError('Invalid source-interface {source_interface}. Interface '
                          'is already a member of bond '
                          '{source_interface_is_bond_member}'.format(**config))

def verify_dhcpv6(config):
    """
    Common helper function used by interface implementations to perform
    recurring validation of DHCPv6 options which are mutually exclusive.
    """
    if 'dhcpv6_options' in config:
        from vyos.util import dict_search

        if {'parameters_only', 'temporary'} <= set(config['dhcpv6_options']):
            raise ConfigError('DHCPv6 temporary and parameters-only options '
                              'are mutually exclusive!')

        # It is not allowed to have duplicate SLA-IDs as those identify an
        # assigned IPv6 subnet from a delegated prefix
        for pd in dict_search('dhcpv6_options.pd', config):
            sla_ids = []
            interfaces = dict_search(f'dhcpv6_options.pd.{pd}.interface', config)

            if not interfaces:
                raise ConfigError('DHCPv6-PD requires an interface where to assign '
                                  'the delegated prefix!')

            for count, interface in enumerate(interfaces):
                if 'sla_id' in interfaces[interface]:
                    sla_ids.append(interfaces[interface]['sla_id'])
                else:
                    sla_ids.append(str(count))

            # Check for duplicates
            duplicates = [x for n, x in enumerate(sla_ids) if x in sla_ids[:n]]
            if duplicates:
                raise ConfigError('Site-Level Aggregation Identifier (SLA-ID) '
                                  'must be unique per prefix-delegation!')

def verify_vlan_config(config):
    """
    Common helper function used by interface implementations to perform
    recurring validation of interface VLANs
    """

    # VLAN and Q-in-Q IDs are not allowed to overlap
    if 'vif' in config and 'vif_s' in config:
        duplicate = list(set(config['vif']) & set(config['vif_s']))
        if duplicate:
            raise ConfigError(f'Duplicate VLAN id "{duplicate[0]}" used for vif and vif-s interfaces!')

    # 802.1q VLANs
    for vlan in config.get('vif', {}):
        vlan = config['vif'][vlan]
        verify_dhcpv6(vlan)
        verify_address(vlan)
        verify_vrf(vlan)

    # 802.1ad (Q-in-Q) VLANs
    for s_vlan in config.get('vif_s', {}):
        s_vlan = config['vif_s'][s_vlan]
        verify_dhcpv6(s_vlan)
        verify_address(s_vlan)
        verify_vrf(s_vlan)

        for c_vlan in s_vlan.get('vif_c', {}):
            c_vlan = s_vlan['vif_c'][c_vlan]
            verify_dhcpv6(c_vlan)
            verify_address(c_vlan)
            verify_vrf(c_vlan)

def verify_accel_ppp_base_service(config):
    """
    Common helper function which must be used by all Accel-PPP services based
    on get_config_dict()
    """
    # vertify auth settings
    if dict_search('authentication.mode', config) == 'local':
        if not dict_search('authentication.local_users', config):
            raise ConfigError('PPPoE local auth mode requires local users to be configured!')

        for user in dict_search('authentication.local_users.username', config):
            user_config = config['authentication']['local_users']['username'][user]

            if 'password' not in user_config:
                raise ConfigError(f'Password required for local user "{user}"')

            if 'rate_limit' in user_config:
                # if up/download is set, check that both have a value
                if not {'upload', 'download'} <= set(user_config['rate_limit']):
                    raise ConfigError(f'User "{user}" has rate-limit configured for only one ' \
                                      'direction but both upload and download must be given!')

    elif dict_search('authentication.mode', config) == 'radius':
        if not dict_search('authentication.radius.server', config):
            raise ConfigError('RADIUS authentication requires at least one server')

        for server in dict_search('authentication.radius.server', config):
            radius_config = config['authentication']['radius']['server'][server]
            if 'key' not in radius_config:
                raise ConfigError(f'Missing RADIUS secret key for server "{server}"')

    if 'gateway_address' not in config:
        raise ConfigError('PPPoE server requires gateway-address to be configured!')

    if 'name_server_ipv4' in config:
        if len(config['name_server_ipv4']) > 2:
            raise ConfigError('Not more then two IPv4 DNS name-servers ' \
                              'can be configured')

    if 'name_server_ipv6' in config:
        if len(config['name_server_ipv6']) > 3:
            raise ConfigError('Not more then three IPv6 DNS name-servers ' \
                              'can be configured')

    if 'client_ipv6_pool' in config:
        ipv6_pool = config['client_ipv6_pool']
        if 'delegate' in ipv6_pool:
            if 'prefix' not in ipv6_pool:
                raise ConfigError('IPv6 "delegate" also requires "prefix" to be defined!')

            for delegate in ipv6_pool['delegate']:
                if 'delegation_prefix' not in ipv6_pool['delegate'][delegate]:
                    raise ConfigError('delegation-prefix length required!')

def verify_diffie_hellman_length(file, min_keysize):
    """ Verify Diffie-Hellamn keypair length given via file. It must be greater
    then or equal to min_keysize """

    try:
        keysize = str(min_keysize)
    except:
        return False

    import os
    import re
    from vyos.util import cmd

    if os.path.exists(file):

        out = cmd(f'openssl dhparam -inform PEM -in {file} -text')
        prog = re.compile('\d+\s+bit')
        if prog.search(out):
            bits = prog.search(out)[0].split()[0]
            if int(bits) >= int(min_keysize):
                return True

    return False

def verify_route_maps(config):
    """
    Common helper function used by routing protocol implementations to perform
    recurring validation if the specified route-map for either zebra to kernel
    installation exists (this is the top-level route_map key) or when a route
    is redistributed with a route-map that it exists!
    """
    if 'route_map' in config:
        route_map = config['route_map']
        # Check if the specified route-map exists, if not error out
        if dict_search(f'policy.route_map.{route_map}', config) == None:
            raise ConfigError(f'Specified route-map "{route_map}" does not exist!')

    if 'redistribute' in config:
        for protocol, protocol_config in config['redistribute'].items():
            if 'route_map' in protocol_config:
                # A hyphen in a route-map name will be converted to _, take care
                # about this effect during validation
                route_map = protocol_config['route_map'].replace('-','_')
                # Check if the specified route-map exists, if not error out
                if dict_search(f'policy.route_map.{route_map}', config) == None:
                    raise ConfigError(f'Redistribution route-map "{route_map}" ' \
                                      f'for "{protocol}" does not exist!')
