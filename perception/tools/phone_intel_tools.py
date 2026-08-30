"""
Phone & Carrier Intelligence Tool for AETHER.
Parses international telephone numbers, resolves carrier, country, line type (Mobile/Fixed/VoIP),
and builds pivots for messaging apps (WhatsApp, Telegram).
"""

from __future__ import annotations

import phonenumbers
from phonenumbers import geocoder, carrier, timezone, PhoneNumberType
from typing import Any, Dict
from aether.perception.tools.registry import BaseTool, ToolResult
from aether.core.logger import logger


class PhoneIntelTool(BaseTool):
    """Deep phone number parsing, carrier discovery, and VoIP/Virtual number classification."""

    def __init__(self):
        super().__init__(
            name="phone_intel",
            description="Parses international phone numbers to extract carrier name, country, region, timezone, line type (Mobile/Fixed/VoIP/Virtual), and messaging pivots.",
            category="Persona OSINT",
            icon="Phone",
            default_param_key="phone",
            example_input="+14155552671",
            params={
                "phone": "Target phone number with country code (e.g. +14155552671 or +447911123456)",
                "country_code": "Optional 2-letter default country ISO (e.g. US, GB, IR)",
            },
        )

    async def execute(self, **kwargs) -> ToolResult:
        raw_phone = kwargs.get("phone") or kwargs.get("number") or kwargs.get("query") or ""
        default_region = kwargs.get("country_code") or kwargs.get("country") or "US"
        raw_phone = str(raw_phone).strip()

        if not raw_phone:
            return ToolResult(success=False, data={}, error="Phone number is required (e.g. +14155552671).")

        logger.info(f"Executing Phone & Carrier Intelligence for: {raw_phone}")

        try:
            parsed = phonenumbers.parse(raw_phone, default_region.upper() if default_region else None)
            is_valid = phonenumbers.is_valid_number(parsed)
            is_possible = phonenumbers.is_possible_number(parsed)

            country_name = geocoder.description_for_number(parsed, "en") or "Unknown"
            carrier_name = carrier.name_for_number(parsed, "en") or "Unassigned / MVNO"
            time_zones = list(timezone.time_zones_for_number(parsed))

            # Determine Line Type
            num_type = phonenumbers.number_type(parsed)
            type_map = {
                PhoneNumberType.MOBILE: "Mobile (Cellular)",
                PhoneNumberType.FIXED_LINE: "Fixed Line (Landline)",
                PhoneNumberType.FIXED_LINE_OR_MOBILE: "Fixed Line or Mobile",
                PhoneNumberType.VOIP: "VoIP (Virtual / Cloud Number)",
                PhoneNumberType.TOLL_FREE: "Toll Free",
                PhoneNumberType.PREMIUM_RATE: "Premium Rate",
                PhoneNumberType.SHARED_COST: "Shared Cost",
                PhoneNumberType.PERSONAL_NUMBER: "Personal Number",
                PhoneNumberType.PAGER: "Pager",
                PhoneNumberType.UAN: "Universal Access Number (UAN)",
                PhoneNumberType.UNKNOWN: "Unknown Line Type",
            }
            line_type = type_map.get(num_type, "Standard Phone")

            formatted_e164 = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
            formatted_intl = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
            formatted_national = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.NATIONAL)
            digits_only = formatted_e164.lstrip("+")

            # Messaging App Link Pivots
            pivots = {
                "whatsapp_direct_chat": f"https://wa.me/{digits_only}",
                "telegram_link": f"https://t.me/+{digits_only}",
                "truecaller_web_search": f"https://www.truecaller.com/search/{country_name.lower()}/{digits_only}",
                "sync_me_search": f"https://sync.me/search/?number={digits_only}",
            }

            return ToolResult(
                success=True,
                data={
                    "raw_input": raw_phone,
                    "is_valid": is_valid,
                    "is_possible": is_possible,
                    "country_code": parsed.country_code,
                    "national_number": parsed.national_number,
                    "country_location": country_name,
                    "carrier_network": carrier_name,
                    "line_type": line_type,
                    "timezones": time_zones,
                    "formats": {
                        "e164": formatted_e164,
                        "international": formatted_intl,
                        "national": formatted_national,
                    },
                    "messaging_app_pivots": pivots,
                    "is_virtual_voip": num_type == PhoneNumberType.VOIP,
                    "summary": f"{formatted_intl} ({country_name}) · {carrier_name} · {line_type}",
                },
            )

        except phonenumbers.NumberParseException as pe:
            logger.warning(f"Phone number parse failed for {raw_phone}: {pe}")
            return ToolResult(success=False, data={"raw_input": raw_phone}, error=f"Invalid phone number format: {pe}")
        except Exception as exc:
            logger.error(f"Phone intel error: {exc}")
            return ToolResult(success=False, data={"raw_input": raw_phone}, error=str(exc))


phone_intel_tool = PhoneIntelTool()
