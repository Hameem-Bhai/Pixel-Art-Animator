# 🎨 Pixel Animator

<div align="center">

```text
░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
█▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀█
█  _    _  _____  _      _____  _______ _____  _    _ _______  █
█ | |  | |/ ____|| |    |_   _||__   __|_   _| | |  | |__   __| █
█ | |__| | (___  | |      | |     | |    | |   | |__| |   | |    █
█ |  __  |\___ \ | |      | |     | |    | |   |  __  |   | |    █
█ | |  | |____) || |____ _| |_    | |   _| |_  | |  | |   | |    █
█ |_|  |_|_____/ |______|_____|   |_|  |_____| |_|  |_|   |_|    █
█▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄█
░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
```

**Bring your pixel art to life with smooth animations!** 🚀

[![Python Version](https://img.shields.io/badge/python-3.7%2B-blue.svg?style=for-the-badge&logo=python)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg?style=for-the-badge)](https://github.com/psf/black)
[![Made with ❤️](https://img.shields.io/badge/Made%20with-❤️-red.svg?style=for-the-badge)]()

</div>

---

## ✨ Features

<div align="center">

| 🎯 Feature | 📝 Description |
|:---:|:---|
| 🖼️ **Pixel Art** | Create beautiful pixel art frames |
| 🎬 **Animation** | Play smooth frame-by-frame animations |
| 💾 **JSON Format** | Save animations in lightweight JSON |
| 🔄 **Loop Support** | Seamless animation looping |
| 🎨 **Custom Colors** | Full RGB color support |
| ⚡ **Fast Rendering** | Optimized for performance |

</div>

---

## 🎬 Animation Preview

<div align="center">

### Frame 1 → Frame 2 → Frame 3 → Loop!

```text
Frame 1          Frame 2          Frame 3
░░░░░░░░        ░░░░░░░░        ░░░░░░░░
░░██░░░░        ░░░░██░░        ░░░░░░██
░░██░░░░   →    ░░░░██░░   →    ░░░░░░██
░░██░░░░        ░░░░██░░        ░░░░░░██
░░░░░░░░        ░░░░░░░░        ░░░░░░░░
  ❤️              ❤️              ❤️
 (left)         (center)        (right)
```

**The heart moves across the screen in a smooth animation!** 💓

</div>

---

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/pixel-animator.git
cd pixel-animator

# Install dependencies
pip install -r requirements.txt

# Or install directly (if published)
# pip install pixel-animator
```

### Usage

```bash
# Run the animator
python pixel_animator.py

# Load a specific animation
python pixel_animator.py --load heart.json

# Export to GIF (if supported)
python pixel_animator.py --export heart.gif
```

### Python API

```python
from pixel_animator import PixelAnimator

# Create animator
animator = PixelAnimator()

# Load animation
animator.load_animation("heart.json")

# Play animation
animator.play(fps=10, loop=True)

# Export to GIF
animator.export_gif("output.gif", fps=10)
```

---

## 📦 JSON Animation Format

Animations are saved in a clean, readable JSON format:

```json
{
  "name": "heart",
  "width": 8,
  "height": 8,
  "fps": 10,
  "frames": [
    {
      "pixels": [
        [0, 0, 0, 0, 0, 0, 0, 0],
        [0, 255, 0, 0, 0, 0, 0, 0],
        [0, 255, 0, 0, 0, 0, 0, 0],
        [0, 255, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0]
      ]
    }
  ]
}
```

---

## 🛠️ Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black pixel_animator.py

# Lint
flake8 pixel_animator.py
```

---

## 📁 Project Structure

```text
pixel-animator/
├── pixel_animator.py      # Main application
├── heart.json             # Example animation
├── requirements.txt       # Dependencies
├── setup.py               # Package setup
├── .gitignore             # Git ignore rules
└── README.md              # This file
```

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the project
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<div align="center">

**Made with 💻 and ☕ by [Hameem](https://github.com/Hameem-Bhai)**

⭐ **Star this repo if you find it useful!** ⭐

```text
░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
█  Thank you for using Pixel Animator! Happy animating! 🎨    █
░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
```

</div>