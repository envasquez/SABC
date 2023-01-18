# -*- coding: utf-8 -*-
import datetime

TODAY: datetime.date = datetime.date.today()
CURRENT_YEAR: int = TODAY.year
CURRENT_MONTH_INT: int = TODAY.month
CURRENT_MONTH_STR: str = TODAY.strftime("%B")
