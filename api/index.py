import json
import base64
from flask import Flask, request, jsonify
import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

app = Flask(__name__)

KEY_IV = b"8080808080808080"

URL = "https://www.hdfcergo.com/OnlineInsurance/MotorOnline/Integration/GetVehicleDetailByRegistrationNo"


def aes_encrypt(text):
    cipher = AES.new(KEY_IV, AES.MODE_CBC, KEY_IV)
    ct_bytes = cipher.encrypt(
        pad(text.encode("utf-8"), AES.block_size)
    )
    return base64.b64encode(ct_bytes).decode("utf-8")


def aes_decrypt(ciphertext):
    try:
        if not ciphertext:
            return None

        ciphertext = ciphertext.strip('"').strip("'")

        raw_data = base64.b64decode(ciphertext)

        cipher = AES.new(KEY_IV, AES.MODE_CBC, KEY_IV)

        pt = unpad(
            cipher.decrypt(raw_data),
            AES.block_size
        )

        return pt.decode("utf-8")

    except Exception:
        return None


def get_vehicle_details(reg_no):
    try:
        enc_reg = aes_encrypt(reg_no)

        payload = {
            "vehicleBasicDetail[RegistrationNumber]": enc_reg,
            "vehicleBasicDetail[IsFromParivahan]": "true"
        }

        headers = {
            "User-Agent": "Mozilla/5.0",
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"
        }

        response = requests.post(
            URL,
            data=payload,
            headers=headers,
            timeout=15
        )

        if response.status_code != 200:
            return None

        try:
            json_obj = response.json()

            if isinstance(json_obj, dict):
                encrypted_data = json_obj.get("Data")
            else:
                encrypted_data = json_obj

        except Exception:
            encrypted_data = response.text

        return aes_decrypt(encrypted_data)

    except Exception:
        return None


@app.route("/")
def home():
    return jsonify({
        "status": "online",
        "service": "Vehicle API",
        "usage": "/get_vehicle?reg=DL3CAB1234"
    })


@app.route("/get_vehicle", methods=["GET"])
def vehicle():

    reg_no = request.args.get("reg")

    if not reg_no:
        return jsonify({
            "status": False,
            "message": "Missing reg parameter"
        }), 400

    reg_no = reg_no.replace(" ", "").upper()

    result = get_vehicle_details(reg_no)

    if not result:
        return jsonify({
            "status": False,
            "message": "Vehicle not found"
        }), 404

    try:
        decrypted_json = json.loads(result)

        info = decrypted_json.get("Data", {})

        p = info.get("ParivahanDetail", {})
        v = info.get("VehicleBasicDetail", {})

        return jsonify({
            "status": True,
            "vehicle_number": reg_no,
            "data": {
                "chassis_number": p.get("ChassisNumber"),
                "engine_number": p.get("EngineNumber"),
                "make": p.get("Make"),
                "model": p.get("Model"),
                "variant": p.get("Variant"),
                "registration_date": p.get("RegistrationDate"),
                "registration_city": v.get("RegistrationCity")
            }
        })

    except Exception:
        return jsonify({
            "status": True,
            "raw_response": result
        })


handler = app
