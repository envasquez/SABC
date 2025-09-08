import os

import yaml

_lakes_data_cache = None


def load_lakes_data():
    global _lakes_data_cache
    if _lakes_data_cache is None:
        lakes_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "lakes.yaml")
        with open(lakes_file, "r") as f:
            _lakes_data_cache = yaml.safe_load(f) if f else {}
    return _lakes_data_cache


def get_lakes_list():
    lakes_data = load_lakes_data()
    lakes = []
    for lake_id, (lake_key, lake_info) in enumerate(lakes_data.items(), 1):
        display_name = lake_info.get("display_name", lake_key.replace("_", " ").title())
        location = "Central Texas"
        lakes.append((lake_id, display_name, location))
    return lakes


def get_ramps_for_lake(lake_id):
    lake_key, lake_info = find_lake_by_id(lake_id)
    if not lake_key:
        return []
    lakes_data = load_lakes_data()
    if lake_key in lakes_data and "ramps" in lakes_data[lake_key]:
        ramps = []
        for ramp_idx, ramp in enumerate(lakes_data[lake_key]["ramps"]):
            ramp_id = f"{lake_key}_{ramp_idx}"
            ramps.append((ramp_id, ramp["name"], lake_id))
        return ramps
    return []


def get_all_ramps():
    lakes_data = load_lakes_data()
    ramps = []
    ramp_id = 1
    for lake_id, (lake_key, lake_info) in enumerate(lakes_data.items(), 1):
        if "ramps" in lake_info:
            for ramp in lake_info["ramps"]:
                ramps.append((ramp_id, ramp["name"], lake_id))
                ramp_id += 1
    return ramps


def find_lake_by_id(lake_id, return_format="full"):
    lakes = get_lakes_list()
    for l_id, name, location in lakes:
        if l_id == lake_id:
            if return_format == "name":
                return name
            lakes_data = load_lakes_data()
            for key, info in lakes_data.items():
                if info.get("display_name", key.replace("_", " ").title()) == name:
                    return key, info
    return None if return_format == "name" else (None, None)


def find_ramp_name_by_id(ramp_id):
    if "_" in str(ramp_id):
        parts = str(ramp_id).rsplit("_", 1)
        if len(parts) == 2:
            lake_key = parts[0]
            ramp_index = int(parts[1])
            lakes = get_lakes_list()
            lake_id = None
            for l_id, l_name, l_location in lakes:
                l_key, l_info = find_lake_by_id(l_id)
                if l_key == lake_key:
                    lake_id = l_id
                    break
            if lake_id is not None:
                ramps_tuples = get_ramps_for_lake(lake_id)
                if 0 <= ramp_index < len(ramps_tuples):
                    return ramps_tuples[ramp_index][1]
    return None


def validate_lake_ramp_combo(lake_id, ramp_id):
    ramps_tuples = get_ramps_for_lake(lake_id)
    if not ramps_tuples:
        return False
    for ramp_tuple in ramps_tuples:
        ramp_id_from_tuple = ramp_tuple[0]
        if ramp_id_from_tuple == str(ramp_id):
            return True
    return False


def find_lake_data_by_db_name(db_lake_name):
    if not db_lake_name:
        return None, None, None
    lakes_data = load_lakes_data()
    db_name_lower = db_lake_name.lower().strip()
    name_mappings = {
        "belton": "belton",
        "travis": "travis",
        "travis night tournament": "travis",
        "lbj": "lbj",
        "lbj night tournament": "lbj",
        "austin": "austin",
        "austin night tournament": "austin",
        "inks": "inks",
        "buchanan": "buchanan",
        "canyon": "canyon_lake",
        "stillhouse hollow": "stillhouse_hollow",
        "fayette county reservoir": "fayette_county_reservoir",
        "walter e. long (decker)": "walter e. long (decker)",
        "bastrop": "bastrop",
        "marble falls": "marble_falls",
        "lady bird": "lady_bird",
        "sommerville": "sommerville",
        "waco": "waco",
        "choke canyon": "choke_canyon",
    }
    yaml_key = name_mappings.get(db_name_lower)
    if yaml_key and yaml_key in lakes_data:
        lake_info = lakes_data[yaml_key]
        display_name = lake_info.get("display_name", yaml_key.replace("_", " ").title())
        return yaml_key, lake_info, display_name
    for key, info in lakes_data.items():
        key_lower = key.lower().replace("_", " ")
        display_lower = info.get("display_name", "").lower()
        if (
            db_name_lower in key_lower
            or key_lower in db_name_lower
            or db_name_lower in display_lower
            or any(word in key_lower for word in db_name_lower.split() if len(word) > 2)
        ):
            display_name = info.get("display_name", key.replace("_", " ").title())
            return key, info, display_name
    return None, None, None
