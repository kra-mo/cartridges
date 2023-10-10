# relative_date.py
#
# Copyright 2022-2023 kramo
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-or-later

from datetime import datetime
from typing import Any

from gi.repository import GLib


def relative_date(timestamp: int) -> Any:  # pylint: disable=too-many-return-statements
    days_no = ((today := datetime.today()) - datetime.fromtimestamp(timestamp)).days

    if days_no == 0:
        return _("Today")
    if days_no == 1:
        return _("Yesterday")
    if days_no <= (day_of_week := today.weekday()):
        return GLib.DateTime.new_from_unix_utc(timestamp).format("%A")
    if days_no <= day_of_week + 7:
        return _("Last Week")
    if days_no <= (day_of_month := today.day):
        return _("This Month")
    if days_no <= day_of_month + 30:
        return _("Last Month")
    if days_no < (day_of_year := today.timetuple().tm_yday):
        return GLib.DateTime.new_from_unix_utc(timestamp).format("%B")
    if days_no <= day_of_year + 365:
        return _("Last Year")
    return GLib.DateTime.new_from_unix_utc(timestamp).format("%Y")
