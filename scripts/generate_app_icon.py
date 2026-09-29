"""
Generates the application icon in PNG and multi-resolution Windows ICO formats.
"""

import os
from PIL import Image, ImageDraw, ImageFont


def generate_icons(output_dir: str):
    os.makedirs(output_dir, exist_ok=True)
    size = 256

    # Create a modern rounded app icon
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Gradient background (blue/navy)
    margin = 12
    draw.rounded_rectangle(
        [margin, margin, size - margin, size - margin],
        radius=48,
        fill=(37, 99, 235),  # Deep Royal Blue #2563eb
        outline=(29, 78, 216),
        width=4
    )

    # Draw document sheet silhouette
    sheet_left = 68
    sheet_top = 54
    sheet_right = 188
    sheet_bottom = 202
    draw.rounded_rectangle(
        [sheet_left, sheet_top, sheet_right, sheet_bottom],
        radius=12,
        fill=(255, 255, 255),
        outline=(226, 232, 240),
        width=2
    )

    # Document header bar
    draw.rounded_rectangle(
        [sheet_left + 16, sheet_top + 20, sheet_right - 16, sheet_top + 34],
        radius=4,
        fill=(203, 213, 225)
    )

    # Document text lines
    for y in [sheet_top + 46, sheet_top + 62, sheet_top + 78]:
        draw.rounded_rectangle(
            [sheet_left + 16, y, sheet_right - 16, y + 6],
            radius=3,
            fill=(226, 232, 240)
        )

    # Checkmark badge in emerald green at bottom right
    badge_center_x = 184
    badge_center_y = 184
    badge_radius = 36
    draw.ellipse(
        [badge_center_x - badge_radius, badge_center_y - badge_radius,
         badge_center_x + badge_radius, badge_center_y + badge_radius],
        fill=(16, 185, 129),  # Emerald #10b981
        outline=(255, 255, 255),
        width=5
    )

    # Checkmark strokes
    draw.line(
        [(badge_center_x - 16, badge_center_y),
         (badge_center_x - 4, badge_center_y + 12),
         (badge_center_x + 16, badge_center_y - 12)],
        fill=(255, 255, 255),
        width=6
    )

    # Save PNG
    png_path = os.path.join(output_dir, "app_icon.png")
    img.save(png_path, format="PNG")

    # Save multi-size ICO
    ico_path = os.path.join(output_dir, "app_icon.ico")
    icon_sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    img.save(ico_path, format="ICO", sizes=icon_sizes)

    print(f"Generated icons: {png_path}, {ico_path}")


if __name__ == "__main__":
    generate_icons(os.path.join("assets", "icons"))
