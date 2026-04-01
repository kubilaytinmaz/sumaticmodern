"""
Test Timer API with correct v2.0 endpoint.
URL: POST /v2.0/cloud/timer/device/{device_id}
"""
import os
import sys
import json
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from dotenv import load_dotenv
load_dotenv()


def main():
    import tinytuya
    print(f"tinytuya version: {tinytuya.version}\n")

    access_id = os.getenv("TUYA_ACCESS_ID")
    access_secret = os.getenv("TUYA_ACCESS_SECRET")
    api_region = os.getenv("TUYA_API_REGION", "eu")

    cloud = tinytuya.Cloud(
        apiRegion=api_region,
        apiKey=access_id,
        apiSecret=access_secret,
        apiDeviceID=""
    )

    device_id = "35004015483fda08ac54"
    now = datetime.now()

    print(f"{'='*60}")
    print(f"Timer API Test - v2.0 Endpoint")
    print(f"{'='*60}\n")

    # 1. Create OFF timer (2 minutes from now)
    turn_off_time = now + timedelta(minutes=2)
    turn_on_time = now + timedelta(minutes=3)

    print(f"Current time: {now.strftime('%H:%M')}")
    print(f"OFF timer: {turn_off_time.strftime('%H:%M')}")
    print(f"ON timer: {turn_on_time.strftime('%H:%M')}\n")

    # 2. Create OFF timer
    print("1. Creating OFF timer...")
    off_payload = {
        "alias_name": "Restart OFF",
        "time": turn_off_time.strftime("%H:%M"),
        "timezone_id": "Europe/Istanbul",
        "date": turn_off_time.strftime("%Y%m%d"),
        "loops": "0000000",
        "functions": [
            {
                "code": "switch_1",
                "value": False
            }
        ]
    }

    uri = f"/v2.0/cloud/timer/device/{device_id}"
    print(f"   POST {uri}")
    print(f"   Payload: {json.dumps(off_payload, indent=2)}")

    resp_off = cloud.cloudrequest(uri, action="POST", post=off_payload)
    print(f"   Response: {json.dumps(resp_off, indent=2)}\n")

    if resp_off.get("success"):
        timer_id_off = resp_off.get("result", {}).get("timer_id")
        print(f"   OFF timer created! ID: {timer_id_off}\n")

        # 3. Create ON timer
        print("2. Creating ON timer...")
        on_payload = {
            "alias_name": "Restart ON",
            "time": turn_on_time.strftime("%H:%M"),
            "timezone_id": "Europe/Istanbul",
            "date": turn_on_time.strftime("%Y%m%d"),
            "loops": "0000000",
            "functions": [
                {
                    "code": "switch_1",
                    "value": True
                }
            ]
        }

        print(f"   Payload: {json.dumps(on_payload, indent=2)}")

        resp_on = cloud.cloudrequest(uri, action="POST", post=on_payload)
        print(f"   Response: {json.dumps(resp_on, indent=2)}\n")

        if resp_on.get("success"):
            timer_id_on = resp_on.get("result", {}).get("timer_id")
            print(f"   ON timer created! ID: {timer_id_on}\n")

            print("=" * 60)
            print("SUCCESS! Both timers created!")
            print(f"OFF at {turn_off_time.strftime('%H:%M')} (ID: {timer_id_off})")
            print(f"ON at {turn_on_time.strftime('%H:%M')} (ID: {timer_id_on})")
            print("These timers will execute LOCALLY on the device!")
            print("=" * 60)
        else:
            print(f"   ON timer failed: {resp_on.get('msg')}")
    else:
        print(f"   OFF timer failed: {resp_off.get('msg')}")
        print(f"   Full response: {json.dumps(resp_off, indent=2)}")

    print(f"\n{'='*60}")
    print("Test complete!")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
