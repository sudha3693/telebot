from html import escape
from decimal import Decimal, InvalidOperation

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


class TelegramUIV2:
    def safe(self, value):
        if value is None or value == "":
            return "N/A"
        return escape(str(value))

    def format_value(self, value, decimals: int = 2):
        if value is None:
            return "N/A"
        if isinstance(value, bool):
            return str(value)

        if isinstance(value, str):
            text = value.strip()
            if not text or text.lower() == "null":
                return "N/A"
            try:
                number = Decimal(text)
            except InvalidOperation:
                return self.safe(value)
        else:
            try:
                number = Decimal(str(value))
            except InvalidOperation:
                return self.safe(value)

        if not number.is_finite():
            return self.safe(value)

        return format(number, f".{decimals}f")

    def status_chip(self, value):
        text = self.safe(value)
        normalized = text.lower()
        if normalized in {"approved", "active", "done", "good", "yes", "y", "healthy"}:
            return f"🟢 {text}"
        if normalized in {"pending", "warning", "review", "hold", "medium"}:
            return f"🟡 {text}"
        if normalized in {"rejected", "blocked", "critical", "bad", "no", "n", "risk"}:
            return f"🔴 {text}"
        return f"🔹 {text}"

    def metric(self, label: str, value):
        return f"<b>{self.safe(label)}:</b> <code>{self.format_value(value)}</code>"

    def format_datetime(self, value):
        if not value:
            return "N/A"
        if hasattr(value, "strftime"):
            return value.strftime("%d-%m-%Y %I:%M %p")
        return self.safe(value)

    def build_home_text(self, display_name: str, telegram_id: str, username: str, role_label: str, access_status: str, total_sites: int, approved_users: int, pending_users: int):
        return (
            "<b>🚀 Telecom Console V2</b>\n"
            "<i>Premium site operations workspace</i>\n\n"
            f"<b>🙌 Welcome:</b> {self.safe(display_name)}\n"
            f"<b>🆔 Telegram ID:</b> <code>{self.safe(telegram_id)}</code>\n"
            f"<b>👤 Username:</b> {self.safe(username)}\n"
            f"<b>👤 Role:</b> {self.safe(role_label)}\n"
            f"<b>🛡 Access:</b> {self.status_chip(access_status)}\n\n"
            "<b>📊 Live Stats</b>\n"
            f"{self.metric('Total Sites', total_sites)}\n"
            f"{self.metric('Active Users', approved_users)}\n"
            f"{self.metric('Pending Requests', pending_users)}\n\n"
            "<b>⚡ Quick Actions</b>\n"
            "🔎 Search Site  •  📊 Dashboard  •  📡 Analytics\n"
            "🛰 Technology  •  🌦 Climate  •  🧹 Hygiene\n"
            "📈 Reports  •  ⭐ Favorites  •  🕘 Recent\n\n"
            "<i>Tap <b>❓ How To Use</b> below for typing examples and full menu guide.</i>"
        )

    def build_home_menu_keyboard(self, is_admin: bool):
        buttons = [
            [
                InlineKeyboardButton("🔎 Search", callback_data="menu|search"),
                InlineKeyboardButton("📊 Dashboard", callback_data="menu|dashboard"),
            ],
            [
                InlineKeyboardButton("👤 Profile", callback_data="menu|profile"),
                InlineKeyboardButton("❓ How To Use", callback_data="menu|howto"),
            ],
            [
                InlineKeyboardButton("📡 Analytics", callback_data="menu|analytics"),
                InlineKeyboardButton("🕘 Recent Searches", callback_data="menu|recent"),
            ],
        ]

        if is_admin:
            buttons.append([InlineKeyboardButton("🛠 Admin Panel", callback_data="menu|admin")])
        return InlineKeyboardMarkup(buttons)

    def build_admin_menu_keyboard(self):
        return InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("👥 Approved Users", callback_data="menu|approved"),
                    InlineKeyboardButton("⏳ Pending Users", callback_data="menu|pending"),
                ],
                [
                    InlineKeyboardButton("🚫 Blocked Users", callback_data="menu|blocked"),
                    InlineKeyboardButton("❌ Rejected Users", callback_data="menu|rejected"),
                ],
                [
                    InlineKeyboardButton("📊 Dashboard", callback_data="menu|dashboard"),
                    InlineKeyboardButton("📈 Stats", callback_data="menu|stats"),
                ],
                [InlineKeyboardButton("🏠 Home", callback_data="menu|home")],
            ]
        )

    def build_dashboard_links_keyboard(self, v1_url: str, v2_url: str):
        return InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("🌐 V1 Dashboard", url=v1_url),
                    InlineKeyboardButton("🌐 V2 Dashboard", url=v2_url),
                ],
                [InlineKeyboardButton("🏠 Home", callback_data="menu|home")],
            ]
        )

    def build_how_to_use_text(self):
        return (
            "<b>❓ How To Use This Bot</b>\n"
            "<i>Simple usage summary</i>\n\n"
            "<b>1. Search a site</b>\n"
            "Type a <b>SITE ID</b> directly in chat.\n"
            "<b>Examples:</b> <code>bhpat01</code>, <code>BHPAT01</code>, <code>Bhpat01</code>\n"
            "<code>bhpat-01</code>, <code>BHPAT-01</code>, <code>Bhpat-01</code>\n"
            "<i>Case and hyphens do not matter.</i>\n\n"
            "<b>2. You can also use commands</b>\n"
            "<code>/site bhpat01</code>\n"
            "<code>/search bhpat-01</code>\n\n"
            "<b>3. Menu Summary</b>\n"
            "🔎 Search Site: find a site\n"
            "📊 Dashboard: open home dashboard\n"
            "📡 Analytics Workspace: trend summary\n"
            "🛰 Site Technology Specification: technology details\n"
            "🌦 Climate Proofing: climate section\n"
            "🧹 Site Asset / Hygiene Update: hygiene section\n"
            "📈 NWA Month Wise / 4G Day Wise: month/day trend reports\n"
            "👤 User Profile: your profile card\n\n"
            "<b>Tip:</b> After opening a site, use the buttons to move between Details, Technology, Climate, Hygiene, and Reports."
        )

    def build_profile_text(self, display_name: str, telegram_id: str, username: str, role_label: str, access_status: str, joined_at, last_active_at):
        return (
            "<b>👤 User Profile</b>\n"
            "<i>Account summary card</i>\n\n"
            f"<b>Name:</b> {self.safe(display_name)}\n"
            f"<b>Telegram ID:</b> <code>{self.safe(telegram_id)}</code>\n"
            f"<b>Username:</b> {self.safe(username)}\n"
            f"<b>Role:</b> {self.safe(role_label)}\n"
            f"<b>Access:</b> {self.status_chip(access_status)}\n"
            f"<b>Joined:</b> {self.safe(self.format_datetime(joined_at))}\n"
            f"<b>Last Active:</b> {self.safe(self.format_datetime(last_active_at))}"
        )

    def build_recent_searches_text(self, site_codes):
        if not site_codes:
            return "<b>🕘 Recent Searches</b>\nNo recent site searches yet."

        lines = [
            f"<b>{index}.</b> <code>{self.safe(code)}</code>"
            for index, code in enumerate(site_codes, start=1)
        ]
        return "<b>🕘 Recent Searches</b>\n" + "\n".join(lines) + "\n\n<i>Tap a site below to open the dashboard.</i>"

    def build_site_search_loading(self, site_query: str):
        return (
            "<b>🔎 Searching Telecom Index</b>\n"
            f"Looking up site <code>{self.safe(site_query)}</code>...\n"
            "<i>Please wait while the dashboard is prepared.</i>"
        )

    def build_site_dashboard_text(self, site, hygiene_row=None, climate_row=None, trend=None):
        site_code = site.site_id or site.site_id_2 or site.sr_id or "N/A"
        hygiene_score = getattr(hygiene_row, "status", None) or "Pending"
        climate_risk = getattr(climate_row, "final_status", None) or "Unknown"
        nwa_status = getattr(trend, "current_site_status", None) or "Unknown"
        battery_status = getattr(site, "eb_status", None) or getattr(site, "eb_non_eb", None) or "Unknown"
        latitude = getattr(site, "lat", None)
        longitude = getattr(site, "long", None)
        location_line = (
            f"<b>Location:</b> <code>{self.format_value(latitude)}</code>, <code>{self.format_value(longitude)}</code>"
            if latitude and longitude
            else "<b>Location:</b> Location not available"
        )

        return (
            "<b>🏢 Site Dashboard</b>\n"
            f"<b>Site:</b> {self.safe(site.airtel_site_name)}\n"
            f"<b>Site ID:</b> <code>{self.safe(site_code)}</code>\n"
            f"<b>Circle/Zone:</b> {self.safe(site.airtel_zone or site.state)}\n"
            f"<b>Technology:</b> {self.safe(site.tech)}\n"
            f"<b>Status:</b> {self.status_chip(getattr(trend, 'current_site_status', None) or 'Live')}\n"
            f"{location_line}\n\n"
            "<b>📌 Quick Metrics</b>\n"
            f"{self.metric('Battery', battery_status)}\n"
            f"{self.metric('DG', site.dg_non_dg)}\n"
            f"{self.metric('Asset', hygiene_score)}\n"
            f"{self.metric('Climate', climate_risk)}\n"
            f"{self.metric('NWA', nwa_status)}\n"
            f"{self.metric('Last Updated', getattr(hygiene_row, 'closure_date_month', None) or getattr(site, 'rfs_date', None) or 'N/A')}\n\n"
            "<i>Select a section below to open detailed data.</i>"
        )

    def build_site_menu_keyboard(self, site_code: str, latitude: str = None, longitude: str = None):
        map_buttons = []
        if latitude and longitude:
            map_url = f"https://www.google.com/maps?q={latitude},{longitude}"
            map_buttons = [[InlineKeyboardButton("📍 Open Google Maps", url=map_url)]]
        else:
            map_buttons = [[InlineKeyboardButton("📍 Open Google Maps", callback_data=f"location|{site_code}")]]
        return InlineKeyboardMarkup(
            map_buttons + [
                [
                    InlineKeyboardButton("📘 Details", callback_data=f"details|{site_code}"),
                    InlineKeyboardButton("🛰 Technology", callback_data=f"tech|{site_code}"),
                ],
                [
                    InlineKeyboardButton("🏗 Other", callback_data=f"other|{site_code}"),
                    InlineKeyboardButton("🧹 Hygiene", callback_data=f"hygiene|{site_code}"),
                ],
                [
                    InlineKeyboardButton("🌦 Climate", callback_data=f"climate|{site_code}"),
                    InlineKeyboardButton("📈 Month Wise", callback_data=f"monthwise|{site_code}"),
                ],
                [
                    InlineKeyboardButton("📉 Day Wise", callback_data=f"daywise|{site_code}"),
                    InlineKeyboardButton("🧾 All", callback_data=f"all|{site_code}"),
                ],
                [
                    InlineKeyboardButton("🏠 Home", callback_data="menu|home"),
                ]
            ]
        )

    def build_back_button(self, site_code: str):
        return InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("⬅ Back", callback_data=f"back|{site_code}"),
                    InlineKeyboardButton("🏠 Home", callback_data="menu|home"),
                ]
            ]
        )

    def build_site_details_text(self, site):
        latitude = getattr(site, "lat", None)
        longitude = getattr(site, "long", None)
        location_line = (
            f"<b>Location:</b> <code>{self.format_value(latitude)}</code>, <code>{self.format_value(longitude)}</code>"
            if latitude and longitude
            else "<b>Location:</b> Location not available"
        )
        return (
            "<b>📘 Site Details</b>\n"
            f"<b>Site ID:</b> <code>{self.safe(site.site_id or site.site_id_2 or 'N/A')}</code>\n"
            f"<b>Site Name:</b> {self.safe(site.airtel_site_name)}\n"
            f"{location_line}\n"
            f"<b>RFS Date:</b> {self.safe(site.rfs_date)}\n"
            f"<b>DG/NON DG:</b> {self.safe(site.dg_non_dg)}\n"
            f"<b>Solar:</b> {self.safe(site.solar_non_solar)}\n"
            f"<b>TOCO:</b> {self.safe(site.main_toco)}\n"
            f"<b>TOCO ID:</b> <code>{self.safe(site.toco_id)}</code>\n"
            f"<b>Airtel Zone:</b> {self.safe(site.airtel_zone)}\n"
            f"<b>District:</b> {self.safe(site.district)}\n"
            f"<b>CEM:</b> {self.safe(getattr(site, 'ztm_name', None) or getattr(site, 'cem', None) or 'N/A')}\n"
            f"<b>Enode-B ID:</b> <code>{self.safe(site.enode_b)}</code>"
        )

    def build_site_technology_text(self, site):
        return (
            "<b>🛰 Site Technology Specification</b>\n"
            f"<b>Site Type:</b> {self.safe(site.site_type)}\n"
            f"<b>No of Link:</b> {self.safe(site.no_of_link)}\n"
            f"<b>Dependency:</b> {self.safe(site.dependency)}\n"
            f"<b>4G Payload:</b> {self.format_value(site.pay_load_4g)}\n"
            f"<b>5G Payload:</b> {self.format_value(site.pay_load_5g)}\n"
            f"<b>5G Available:</b> {self.safe(site.available_5g)}\n"
            f"<b>Tech:</b> {self.safe(site.tech)}\n"
            f"<b>DG/Non DG:</b> {self.safe(site.dg_non_dg)}"
        )

    def build_site_other_text(self, site):
        return (
            "<b>🏗 Site Other Specification</b>\n"
            f"<b>Dependency:</b> {self.safe(site.dependency)}\n"
            f"<b>MS Avg Churn:</b> {self.format_value(site.ms_avg_churn)}\n"
            f"<b>Opex Cost:</b> {self.format_value(site.opex_cost)}"
        )

    def build_asset_hygiene_text(self, row):
        if not row:
            return "<b>🧹 Site Asset / Hygiene Update</b>\nNo hygiene or asset record found for this site."
        return (
            "<b>🧹 Site Asset / Hygiene Update</b>\n"
            f"<b>Site Name:</b> {self.safe(row.site_name)}\n"
            f"<b>Principal Owner:</b> {self.safe(row.principal_owner)}\n"
            f"<b>DG/Non-DG:</b> {self.safe(row.dg_non_dg)}\n"
            f"<b>DG Deployment:</b> {self.safe(getattr(row, 'dg_deployment', None))}\n"
            f"<b>BB Deployment:</b> {self.safe(getattr(row, 'bb_deployment', None))}\n"
            f"<b>Solar Deployment:</b> {self.safe(getattr(row, 'solar_deployment', None))}\n"
            f"<b>Bucket/Category:</b> {self.safe(row.bucket_category)}\n"
            f"<b>Closure Date/Month:</b> {self.safe(row.closure_date_month)}\n"
            f"<b>Month:</b> {self.safe(row.month)}\n"
            f"<b>Bucket:</b> {self.safe(row.bucket)}\n"
            f"<b>Status:</b> {self.status_chip(row.status)}"
        )

    def build_climate_proofing_text(self, row):
        if not row:
            return "<b>🌦 Climate Proofing</b>\nNo climate proofing record found for this site."
        return (
            "<b>🌦 Climate Proofing</b>\n"
            f"<b>Circle:</b> {self.safe(row.circle)}\n"
            f"<b>Cluster:</b> {self.safe(row.cluster)}\n"
            f"<b>District:</b> {self.safe(row.district)}\n"
            f"<b>BZ:</b> {self.safe(row.bz)}\n"
            f"<b>Activity:</b> {self.format_value(row.activity)}\n"
            f"<b>Final Status:</b> {self.status_chip(row.final_status)}\n"
            f"<b>Remarks:</b> {self.safe(row.remarks)}"
        )

    def build_nwa_month_wise_text(self, trend):
        if not trend:
            return "<b>📈 NWA - Month Wise</b>\nNo trend data found for this site."
        months = [
            ("Nov '22", trend.nov_22), ("Dec '22", trend.dec_22),
            ("Jan '23", trend.jan_23), ("Feb '23", trend.feb_23),
            ("Mar '23", trend.mar_23), ("Apr '23", trend.apr_23),
            ("May '23", trend.may_23), ("Jun '23", trend.jun_23),
            ("Jul '23", trend.jul_23), ("Aug '23", trend.aug_23),
            ("Sep '23", trend.sep_23), ("Oct '23", trend.oct_23),
            ("Nov '23", trend.nov_23), ("Dec '23", trend.dec_23),
            ("Jan '24", trend.jan_24), ("Feb '24", trend.feb_24),
            ("Mar '24", trend.mar_24), ("Apr '24", trend.apr_24),
            ("May '24", trend.may_24), ("Jun '24", trend.jun_24),
            ("Jul '24", trend.jul_24), ("Aug '24", trend.aug_24),
            ("Sep '24", trend.sep_24), ("Oct '24", trend.oct_24),
            ("Nov '24", trend.nov_24), ("Dec '24", trend.dec_24),
            ("Jan '25", trend.jan_25), ("Feb '25", trend.feb_25),
            ("Mar '25", trend.mar_25), ("Apr '25", trend.apr_25),
            ("May '25", trend.may_25), ("Jun '25", trend.jun_25),
            ("Jul '25", trend.jul_25), ("Aug '25", trend.aug_25),
            ("Sep '25", trend.sep_25), ("Oct '25", trend.oct_25),
            ("Nov '25", trend.nov_25), ("Dec '25", trend.dec_25),
            ("Jan-26", trend.jan_26), ("Feb-26", trend.feb_26),
            ("Mar-26", trend.mar_26), ("Apr-26", trend.apr_26),
            ("May-26", trend.may_26), ("Jun-26", trend.jun_26),
            ("Jul-26", trend.jul_26), ("Aug-26", trend.aug_26),
            ("Sep-26", trend.sep_26), ("Oct-26", trend.oct_26),
            ("Nov-26", trend.nov_26), ("Dec-26", trend.dec_26),
        ]
        lines = [f"<b>{self.safe(label)}:</b> {self.format_value(value)}" for label, value in months]
        return "<b>📈 NWA - Month Wise</b>\n" + "\n".join(lines)

    def build_nwa_trend_daywise_text(self, trend):
        if not trend:
            return "<b>📉 NWA Trend - Daywise</b>\nNo trend data found for this site."
        current = getattr(trend, "current_site_status", None) or "Unknown"
        mtd_incidence = getattr(trend, "mtd_incidence", None)
        nov_incidence = getattr(trend, "fifth_nov_incidence", None)
        return (
            "<b>📉 NWA Trend - Daywise</b>\n"
            f"<b>Current Status:</b> {self.status_chip(current)}\n"
            f"<b>5th Nov Incidence:</b> {self.format_value(nov_incidence)}\n"
            f"<b>MTD Incidence:</b> {self.format_value(mtd_incidence)}"
        )

    def build_daywise_trend_text(self, payload):
        if not payload:
            return "<b>📉 4G Day Wise Trend</b>\nNo day-wise trend data found for this site."

        summary_lines = [
            "<b>📉 4G Day Wise Trend</b>",
            f"<b>Site ID:</b> <code>{self.safe(payload.get('site_id'))}</code>",
            f"<b>Cluster:</b> {self.safe(payload.get('cluster'))}",
            f"<b>Current Status:</b> {self.status_chip(payload.get('current_site_status') or 'Unknown')}",
            f"<b>Owner Issue Sites:</b> {self.format_value(payload.get('owner_issue_sites'))}",
            f"<b>5G:</b> {self.format_value(payload.get('five_g'))}",
            f"<b>District:</b> {self.safe(payload.get('district'))}",
            f"<b>Circle:</b> {self.safe(payload.get('circle'))}",
            f"<b>DZ:</b> {self.safe(payload.get('dz'))}",
        ]

        trend_points = payload.get("trend_points") or []
        if not trend_points:
            summary_lines.append("\n<i>No populated day-wise date values were found for this site.</i>")
            return "\n".join(summary_lines)

        trend_lines = [
            f"<b>{self.safe(point.get('label'))}:</b> {self.format_value(point.get('value'))}"
            for point in trend_points
        ]
        return "\n".join(summary_lines + ["", "<b>Date Trends</b>"] + trend_lines)