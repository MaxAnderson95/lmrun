import fire
import json
import logicmonitor_sdk
import sys
import random
from logicmonitor_sdk import LMApi
from pathlib import Path


def parse_extension(file: Path):
    return file.suffix


def read_file(file: Path):
    with open(file, 'r', encoding="utf-8-sig") as f:  # utf-8-sig handles with and w/o BOM
        script = f.read().strip()
    return script


def connect_to_lm(creds):
    configuration = logicmonitor_sdk.Configuration()
    configuration.company = creds.get('account_name')
    configuration.access_id = creds.get('access_id')
    configuration.access_key = creds.get('access_key')

    api_instance = logicmonitor_sdk.LMApi(
        logicmonitor_sdk.ApiClient(configuration))
    return api_instance


def submit_script(script: str, type: str, api_instance: LMApi, collector_id: int):

    if type == ".groovy":
        command = "groovy"
    elif type == ".ps1":
        command = "posh"
    else:
        raise TypeError("Input file must be .groovy or .ps1")

    body = {"cmdline": f"!{command} \n {script}"}

    thread = api_instance.execute_debug_command(
        async_req=True, body=body, collector_id=collector_id,)

    result = thread.get()

    return result.session_id


def get_script_result(session_id: str, api_instance: LMApi, collector_id: int):
    response = api_instance.get_debug_command_result(
        id=session_id, collector_id=collector_id)

    return response.output


def get_config_file_path():
    home = Path.home()
    return home.joinpath(".lmrun/config.json")


def get_login_credentials():
    path = get_config_file_path()
    try:
        with open(path, 'r') as f:
            content = f.read()
    except FileNotFoundError:
        print("Please login first by running 'lmrun login'")
        sys.exit(1)
    except Exception:
        print("An error occured while getting credential file from local storage.")
        sys.exit(1)
    creds = json.loads(content)
    return creds


def get_random_collector(api_instance: LMApi):
    collectors = api_instance.get_collector_list().items
    return random.choice(collectors).id


def command_login(account_name: str = None, access_id: str = None, access_key: str = None):
    if account_name == None:
        account_name = input(
            "Please enter your LogicMonitor account name: ").strip()
    if access_id == None:
        access_id = input("Please enter the API access id: ").strip()
    if access_key == None:
        access_key = input("Please enter the API access key: ").strip()

    config_file = get_config_file_path()
    file_contents = {
        "account_name": account_name,
        "access_id": access_id,
        "access_key": access_key
    }
    parent_dir = config_file.parent
    parent_dir.mkdir(parents=True, exist_ok=True)
    with config_file.open(mode="w") as f:
        f.write(json.dumps(file_contents, indent=1))


def command_logout():
    path = get_config_file_path()
    path.unlink()


def command_run(path: str, collector_id: int = None):
    creds = get_login_credentials()
    api = connect_to_lm(creds)
    path = Path(path)  # Convert to Path obj
    script = read_file(path)
    if collector_id == None:
        collector_id = get_random_collector(api)
    session_id = submit_script(
        script, parse_extension(path), api, collector_id)
    result = get_script_result(session_id, api, collector_id)
    print(result)


def main():
    fire.Fire({
        "login": command_login,
        "run": command_run,
        "logout": command_logout
    })


if __name__ == "__main__":
    main()