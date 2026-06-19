"""Calculate an HX711 calibration factor from averaged raw readings."""

import argparse
from decimal import Decimal, InvalidOperation


def calibration_factor(tare_raw, loaded_raw, known_kg):
    tare = Decimal(str(tare_raw))
    loaded = Decimal(str(loaded_raw))
    mass = Decimal(str(known_kg))
    if mass <= 0:
        raise ValueError("known_kg must be greater than zero")
    delta = loaded - tare
    if delta == 0:
        raise ValueError("loaded_raw must differ from tare_raw")
    return delta / mass


def main():
    parser = argparse.ArgumentParser(
        description="Calculate the raw HX711 counts represented by one kilogram."
    )
    parser.add_argument("--tare-raw", required=True, help="Average raw reading with an empty scale")
    parser.add_argument("--loaded-raw", required=True, help="Average raw reading with the known mass")
    parser.add_argument("--known-kg", required=True, help="Known calibration mass in kilograms")
    args = parser.parse_args()

    try:
        factor = calibration_factor(args.tare_raw, args.loaded_raw, args.known_kg)
    except (InvalidOperation, ValueError) as exc:
        parser.error(str(exc))

    print(f"tare_offset={Decimal(args.tare_raw)}")
    print(f"counts_per_kg={factor}")
    print(f"tatobari_reference_unit_counts_per_gram={factor / Decimal('1000')}")
    print("weight_kg = (raw_reading - tare_offset) / counts_per_kg")


if __name__ == "__main__":
    main()
