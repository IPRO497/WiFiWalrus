import platform, random , subprocess, math

class NetworkScanner:
    def _rank_network(self, network):
        # Security Scoring
        security_scores = {
            'WPA3-ENTERPRISE': 50,
            'WPA3-PERSONAL': 45,
            'WPA3': 40, 
            'WPA2-ENTERPRISE': 35,
            'WPA2-PERSONAL': 30,
            'WPA2': 25,
            'WPA': 20,
            'WEP': 10,
            'OPEN': 0
        }
        # Parse the security string to check for the presence of -Enterprise or -Personal
        security = network.get('Authentication', '').upper().replace('-', ' ')
        security_components = security.split()

        # Default security type is OPEN if none is specified
        if not security_components:
            security_key = 'OPEN'
        elif 'ENTERPRISE' in security_components:
            security_key = f'{security_components[0]}-ENTERPRISE'
        elif 'PERSONAL' in security_components:
            security_key = f'{security_components[0]}-PERSONAL'
        else:
            security_key = security_components[0]  # For 'WEP' or 'OPEN' or generic types
        
        security_score = security_scores.get(security_key, security_scores.get(security_key, 0))

        # Signal Strength Scoring (Logarithmic mapping)
        signal_strength = int(network.get('Signal', '0%').rstrip('%'))
        # Logarithmic mapping: The score increases rapidly for lower signal strengths and more slowly for higher strengths.
        # Adding 1 to avoid log(0) and scaling to fit into the 0-30 range
        signal_score = 30 * (math.log10(signal_strength + 1) / math.log10(101))

        # SSID Scoring
        common_ssids = [
            'default', 'linksys', 'netgear', 'xfinity', 'home', 'admin', 'user', 'guest', 
            '1234', 'public', 'free', 'wifi', 'mywifi', 'wireless'
        ]
        # Safely get the SSID, default to an empty string if not present
        ssid = network.get('SSID', '').lower()
        ssid_score = 10 if any(common_name in ssid for common_name in common_ssids) else 20

        # Total Score Calculation
        total_score = security_score + signal_score + ssid_score

        # Ensure the score doesn't exceed 100
        total_score = min(total_score, 100)

        network['Score'] = round(total_score)
        return network

    def _parse_network_data(self, raw_data):
        networks = []
        current_network = {}
        for line in raw_data.split('\n'):
            line = line.strip()
            if line.startswith("SSID"):
                if current_network:  # If there is a network already, add it to the list
                    self._rank_network(current_network)
                    networks.append(current_network)
                    current_network = {}
                ssid = line.split(':', 1)[1].strip() if ':' in line else "N/A"
                current_network['SSID'] = ssid
            elif line.startswith("BSSID"):
                bssid = line.split(':', 1)[1].strip() if ':' in line else "N/A"
                current_network['BSSID'] = bssid
            elif line.startswith("Signal"):
                signal = line.split(':', 1)[1].strip() if ':' in line else "0%"
                current_network['Signal'] = signal
            elif line.startswith("Authentication"):
                auth = line.split(':', 1)[1].strip() if ':' in line else "N/A"
                current_network['Authentication'] = auth

        if current_network:  # Check if there is a network pending to be added
            self._rank_network(current_network)
            networks.append(current_network)
        return networks
    
    def _get_fake_network_data(self):
        fake_networks = []
        for _ in range(10):
            # Decide whether to use a common SSID or a unique one
            use_common_ssid = random.choice([True, False])
            common_ssids = ['default', 'linksys', 'netgear', 'xfinity']
            ssid = random.choice(common_ssids) if use_common_ssid else f"Network_{random.randint(1, 100)}"

            signal = f"{random.randint(20, 100)}%"
            auth_options = ['WPA3-ENTERPRISE', 'WPA3-PERSONAL', 'WPA3', 'WPA2-Enterprise', 'WPA2-Personal', 'WPA2', 'WPA', 'WEP', 'OPEN']
            authentication = random.choice(auth_options)

            fake_networks.append({
                'SSID': ssid,
                'BSSID': ':'.join('%02x' % random.randint(0, 255) for _ in range(6)),
                'Signal': signal,
                'Authentication': authentication
            })

        # Generate the fake network data as a string
        fake_network_data = "\n".join([
            f"SSID: {net['SSID']}\nBSSID: {net['BSSID']}\nSignal: {net['Signal']}\nAuthentication: {net['Authentication']}"
            for net in fake_networks
        ])

        return fake_network_data

    def scan(self):
        networks_raw = ''
        if platform.system() == 'Windows':
            try:
                process = subprocess.Popen(['netsh', 'wlan', 'show', 'networks', 'mode=Bssid'],
                                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                networks_raw, error = process.communicate(timeout=30)
                if process.returncode != 0:
                    print(f"Command failed with error: {error}")
                    return []
            except subprocess.TimeoutExpired:
                print("Scanning process timed out.")
                return []
        else:
            networks_raw = self._get_fake_network_data()

        parsed_networks = self._parse_network_data(networks_raw)
        ranked_networks = [self._rank_network(network) for network in parsed_networks]
        ranked_networks.sort(key=lambda x: x['Score'], reverse=True)
        # Return only the top 10 networks
        top_networks = ranked_networks[:10]
        return top_networks
    