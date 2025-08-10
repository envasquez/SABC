# -*- coding: utf-8 -*-
import calendar as cal
from datetime import date
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont


def generate_calendar_image(year, events_by_date, width=1200, height=900):
    """Generate a 12-month calendar image similar to the PDF"""

    # Create image with white background
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    # Try to load fonts, fall back to default if not available
    try:
        title_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
        month_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 16)
        day_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 12)
        small_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 10)
    except (OSError, IOError):
        # Fall back to default font
        title_font = ImageFont.load_default()
        month_font = ImageFont.load_default()
        day_font = ImageFont.load_default()
        small_font = ImageFont.load_default()

    # Colors
    colors = {
        "black": (0, 0, 0),
        "gray": (128, 128, 128),
        "light_gray": (220, 220, 220),
        "tournament": (40, 167, 69),  # Green for tournaments only
        "border": (200, 200, 200),
        "header_bg": (248, 249, 250),
    }

    # Title
    title = f"SABC {year}"
    title_bbox = draw.textbbox((0, 0), title, font=title_font)
    title_width = title_bbox[2] - title_bbox[0]
    draw.text(
        ((width - title_width) // 2, 20), title, fill=colors["black"], font=title_font
    )

    # Calendar layout: 3 columns, 4 rows
    cols = 3
    rows = 4
    margin = 40
    spacing = 20

    calendar_width = width - (2 * margin)
    calendar_height = height - 80  # Leave space for title and legend

    month_width = (calendar_width - (spacing * (cols - 1))) // cols
    month_height = (
        calendar_height - (spacing * (rows - 1)) - 60
    ) // rows  # 60 for legend

    month_names = [
        "JANUARY",
        "FEBRUARY",
        "MARCH",
        "APRIL",
        "MAY",
        "JUNE",
        "JULY",
        "AUGUST",
        "SEPTEMBER",
        "OCTOBER",
        "NOVEMBER",
        "DECEMBER",
    ]

    day_names = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"]

    for month_num in range(1, 13):
        # Calculate position
        col = (month_num - 1) % cols
        row = (month_num - 1) // cols

        x = margin + col * (month_width + spacing)
        y = 70 + row * (month_height + spacing)

        # Month border
        draw.rectangle(
            [x, y, x + month_width, y + month_height], outline=colors["border"], width=1
        )

        # Month header
        header_height = 25
        draw.rectangle(
            [x, y, x + month_width, y + header_height],
            fill=colors["header_bg"],
            outline=colors["border"],
            width=1,
        )

        # Month name
        month_name = month_names[month_num - 1]
        month_bbox = draw.textbbox((0, 0), month_name, font=month_font)
        month_text_width = month_bbox[2] - month_bbox[0]
        draw.text(
            (x + (month_width - month_text_width) // 2, y + 5),
            month_name,
            fill=colors["black"],
            font=month_font,
        )

        # Day headers
        day_header_y = y + header_height
        day_header_height = 20
        day_width = month_width // 7

        for i, day_name in enumerate(day_names):
            day_x = x + i * day_width
            draw.rectangle(
                [
                    day_x,
                    day_header_y,
                    day_x + day_width,
                    day_header_y + day_header_height,
                ],
                fill=colors["light_gray"],
                outline=colors["border"],
                width=1,
            )

            day_bbox = draw.textbbox((0, 0), day_name, font=small_font)
            day_text_width = day_bbox[2] - day_bbox[0]
            draw.text(
                (day_x + (day_width - day_text_width) // 2, day_header_y + 3),
                day_name,
                fill=colors["gray"],
                font=small_font,
            )

        # Calendar days
        month_cal = cal.monthcalendar(year, month_num)
        calendar_start_y = day_header_y + day_header_height
        day_height = (month_height - header_height - day_header_height) // 6

        today = date.today()

        for week_num, week in enumerate(month_cal):
            for day_num, day in enumerate(week):
                if day == 0:
                    continue

                day_x = x + day_num * day_width
                day_y = calendar_start_y + week_num * day_height

                # Check for events on this day
                day_date = date(year, month_num, day)
                date_key = day_date.strftime("%Y-%m-%d")
                day_events = events_by_date.get(date_key, [])

                # Determine background color - only tournaments matter
                bg_color = "white"
                if day_events and any(e["type"] == "tournament" for e in day_events):
                    bg_color = "tournament"

                # Draw day cell
                cell_color = (
                    colors.get(bg_color, colors["black"])
                    if bg_color != "white"
                    else (255, 255, 255)
                )
                draw.rectangle(
                    [day_x, day_y, day_x + day_width, day_y + day_height],
                    fill=cell_color,
                    outline=colors["border"],
                    width=1,
                )

                # Day number
                day_str = str(day)
                day_bbox = draw.textbbox((0, 0), day_str, font=day_font)
                day_text_width = day_bbox[2] - day_bbox[0]
                day_text_height = day_bbox[3] - day_bbox[1]

                # Text color - white on tournament days, black on white
                text_color = colors["black"] if bg_color == "white" else (255, 255, 255)

                # Highlight today
                if day_date == today:
                    text_color = (255, 255, 255)
                    if bg_color == "white":
                        draw.rectangle(
                            [day_x, day_y, day_x + day_width, day_y + day_height],
                            fill=(13, 110, 253),
                            outline=colors["border"],
                            width=1,
                        )

                draw.text(
                    (
                        day_x + (day_width - day_text_width) // 2,
                        day_y + (day_height - day_text_height) // 2,
                    ),
                    day_str,
                    fill=text_color,
                    font=day_font,
                )

    # Simple legend at bottom - just tournaments
    legend_y = height - 40
    legend_text = "■ Tournament Days"

    # Center the legend
    legend_bbox = draw.textbbox((0, 0), legend_text, font=small_font)
    legend_width = legend_bbox[2] - legend_bbox[0]
    legend_start_x = (width - legend_width - 20) // 2

    # Color box
    draw.rectangle(
        [legend_start_x, legend_y, legend_start_x + 15, legend_y + 15],
        fill=colors["tournament"],
        outline=colors["border"],
        width=1,
    )

    # Label
    draw.text(
        (legend_start_x + 20, legend_y),
        "Tournament Days",
        fill=colors["black"],
        font=small_font,
    )

    return img


def calendar_image_to_bytes(img, format="PNG"):
    """Convert PIL image to bytes for HTTP response"""
    buffer = BytesIO()
    img.save(buffer, format=format)
    buffer.seek(0)
    return buffer.getvalue()
