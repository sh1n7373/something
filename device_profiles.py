import random

ANDROID_DEVICES = [
    ("Samsung Galaxy S24 Ultra", "14", "SM-S928B"),
    ("Samsung Galaxy S24+", "14", "SM-S926B"),
    ("Samsung Galaxy S24", "14", "SM-S921B"),
    ("Samsung Galaxy S23 Ultra", "13", "SM-S918B"),
    ("Samsung Galaxy S23+", "13", "SM-S916B"),
    ("Samsung Galaxy S23", "13", "SM-S911B"),
    ("Samsung Galaxy A54 5G", "13", "SM-A546B"),
    ("Samsung Galaxy A34 5G", "13", "SM-A346B"),
    ("Google Pixel 8 Pro", "14", "GP8P"),
    ("Google Pixel 8", "14", "GP8"),
    ("Google Pixel 7 Pro", "13", "GP7P"),
    ("Google Pixel 7", "13", "GP7"),
    ("OnePlus 12", "14", "CPH2573"),
    ("OnePlus 11", "13", "CPH2449"),
    ("OnePlus Nord 3", "13", "CPH2493"),
    ("Xiaomi 14 Pro", "14", "2312DPL48G"),
    ("Xiaomi 14", "14", "23127PN0CC"),
    ("Xiaomi 13 Pro", "13", "2210132G"),
    ("Xiaomi Redmi Note 13 Pro+", "13", "23090RA98G"),
    ("Xiaomi Redmi Note 12 Pro", "12", "22101316G"),
    ("Oppo Find X6 Pro", "13", "PGEM10"),
    ("Oppo Reno 10 Pro+", "13", "CPH2525"),
    ("Realme GT 5 Pro", "14", "RMX3888"),
    ("Realme 11 Pro+", "13", "RMX3741"),
    ("Vivo X100 Pro", "14", "V2307A"),
    ("Vivo X90 Pro+", "13", "V2145A"),
    ("Sony Xperia 1 V", "13", "XQ-DQ72"),
    ("Sony Xperia 5 V", "13", "XQ-DE72"),
    ("Motorola Edge 40 Pro", "13", "XT2301-4"),
    ("Nothing Phone 2", "13", "A065"),
]

ANDROID_APP_VERSIONS = [
    "10.3.2", "10.2.9", "10.1.1", "10.0.5",
    "9.9.3", "9.8.4", "9.7.2", "9.6.8",
    "9.5.3", "9.4.1",
]

IOS_DEVICES = [
    ("iPhone 15 Pro Max", "17.2.1"),
    ("iPhone 15 Pro", "17.2"),
    ("iPhone 15 Plus", "17.1.2"),
    ("iPhone 15", "17.1"),
    ("iPhone 14 Pro Max", "17.0.3"),
    ("iPhone 14 Pro", "16.7.2"),
    ("iPhone 14 Plus", "16.7.1"),
    ("iPhone 14", "16.7"),
    ("iPhone 13 Pro Max", "16.6.1"),
    ("iPhone 13 Pro", "16.6"),
    ("iPhone 13", "16.5.1"),
    ("iPhone 13 mini", "16.5"),
    ("iPhone 12 Pro Max", "16.4.1"),
    ("iPhone 12 Pro", "16.4"),
    ("iPhone 12", "16.3.1"),
    ("iPad Pro 12.9 M2", "17.1"),
    ("iPad Pro 11 M2", "16.6"),
    ("iPad Air 5", "16.5"),
    ("iPad mini 6", "16.4"),
    ("iPad 10th Gen", "16.3"),
]

IOS_APP_VERSIONS = [
    "9.6.3", "9.5.8", "9.5.2", "9.4.6",
    "9.4.2", "9.3.6", "9.3.1", "9.2.5",
    "9.2.1", "9.1.4",
]

DESKTOP_CONFIGS = [
    ("Windows 11 Home 23H2", "Windows", "4.10.3", "x86_64"),
    ("Windows 11 Pro 22H2", "Windows", "4.9.8", "x86_64"),
    ("Windows 10 Home 22H2", "Windows", "4.10.3", "x86_64"),
    ("Windows 10 Pro 21H2", "Windows", "4.9.2", "x86_64"),
    ("Windows 10 Home 21H1", "Windows", "4.8.4", "x86_64"),
    ("Windows 10 Pro 20H2", "Windows", "4.7.3", "x86_64"),
    ("Windows 10 LTSC 2021", "Windows", "4.6.7", "x86_64"),
    ("macOS 14.2 Sonoma", "macOS", "4.10.3", "arm64"),
    ("macOS 14.1 Sonoma", "macOS", "4.9.8", "arm64"),
    ("macOS 13.6 Ventura", "macOS", "4.10.3", "x86_64"),
    ("macOS 13.5 Ventura", "macOS", "4.9.2", "x86_64"),
    ("macOS 12.7 Monterey", "macOS", "4.8.1", "x86_64"),
    ("macOS 12.6 Monterey", "macOS", "4.7.2", "arm64"),
    ("macOS 11.7 Big Sur", "macOS", "4.6.3", "x86_64"),
    ("Ubuntu 23.10 Mantic", "Linux", "4.10.3", "x86_64"),
    ("Ubuntu 23.04 Lunar", "Linux", "4.9.1", "x86_64"),
    ("Ubuntu 22.04.3 LTS", "Linux", "4.8.4", "x86_64"),
    ("Ubuntu 20.04.6 LTS", "Linux", "4.7.3", "x86_64"),
    ("Debian 12.3 Bookworm", "Linux", "4.10.3", "x86_64"),
    ("Debian 11.8 Bullseye", "Linux", "4.8.1", "x86_64"),
    ("Fedora Linux 39", "Linux", "4.10.3", "x86_64"),
    ("Fedora Linux 38", "Linux", "4.9.2", "x86_64"),
    ("Arch Linux 2024.01", "Linux", "4.10.3", "x86_64"),
    ("Arch Linux 2023.12", "Linux", "4.9.8", "x86_64"),
    ("Manjaro Linux 23.1", "Linux", "4.9.1", "x86_64"),
    ("Linux Mint 21.2", "Linux", "4.8.4", "x86_64"),
    ("openSUSE Tumbleweed", "Linux", "4.10.3", "x86_64"),
    ("openSUSE Leap 15.5", "Linux", "4.7.3", "x86_64"),
    ("Pop!_OS 22.04", "Linux", "4.8.1", "x86_64"),
    ("CentOS Stream 9", "Linux", "4.6.7", "x86_64"),
    ("Rocky Linux 9.3", "Linux", "4.9.2", "x86_64"),
    ("AlmaLinux 9.3", "Linux", "4.8.4", "x86_64"),
    ("Kali Linux 2024.1", "Linux", "4.10.3", "x86_64"),
    ("EndeavourOS 23.10", "Linux", "4.9.1", "x86_64"),
    ("Garuda Linux", "Linux", "4.10.3", "x86_64"),
    ("NixOS 23.11", "Linux", "4.9.8", "x86_64"),
    ("Zorin OS 17", "Linux", "4.8.1", "x86_64"),
    ("elementary OS 7.1", "Linux", "4.7.3", "x86_64"),
    ("void Linux", "Linux", "4.6.2", "x86_64"),
    ("Gentoo Linux 23.0", "Linux", "4.10.3", "x86_64"),
]

LANG_CODES = [
    "en", "en-US", "en-GB", "ru", "de",
    "fr", "es", "it", "pt", "tr",
    "uk", "pl", "nl", "sv", "da",
    "fi", "nb", "ko", "ja", "zh-hans",
]


def _random_android():
    device, android_ver, build = random.choice(ANDROID_DEVICES)
    app_ver = random.choice(ANDROID_APP_VERSIONS)
    lang = random.choice(LANG_CODES)
    minor = random.randint(1, 50)
    patch = random.randint(100, 500)
    sdk = {"14": "34", "13": "33", "12": "32"}.get(android_ver, "33")
    return {
        "device_model": device,
        "system_version": f"Android {android_ver}; {build} Build/UP1A.231005.00{minor}",
        "app_version": app_ver,
        "lang_code": lang,
        "system_lang_code": lang,
        "_profile_label": f"{device} / Android {android_ver}",
        "_type": "android",
    }


def _random_ios():
    device, ios_ver = random.choice(IOS_DEVICES)
    app_ver = random.choice(IOS_APP_VERSIONS)
    lang = random.choice(LANG_CODES)
    build_chars = "ABCDEFGHIJK"
    build = f"{random.randint(20,23)}{random.choice(build_chars)}{random.randint(100,999)}"
    return {
        "device_model": device,
        "system_version": f"{ios_ver} ({build})",
        "app_version": app_ver,
        "lang_code": lang,
        "system_lang_code": lang,
        "_profile_label": f"{device} / iOS {ios_ver}",
        "_type": "ios",
    }


def _random_desktop():
    sys_ver, platform, app_ver, arch = random.choice(DESKTOP_CONFIGS)
    lang = random.choice(LANG_CODES)
    return {
        "device_model": f"{platform} {arch}",
        "system_version": sys_ver,
        "app_version": app_ver,
        "lang_code": lang,
        "system_lang_code": lang,
        "_profile_label": f"{sys_ver} ({arch})",
        "_type": "desktop",
    }


_generators = {
    "android": _random_android,
    "ios": _random_ios,
    "desktop": _random_desktop,
}


def random_fingerprint(device_type="random"):
    if device_type in _generators:
        return _generators[device_type]()
    return random.choice(list(_generators.values()))()


def get_client_kwargs(acc):
    fp = acc.get("fingerprint")
    if not fp:
        fp = random_fingerprint("random")
    return {k: v for k, v in fp.items() if not k.startswith("_")}
