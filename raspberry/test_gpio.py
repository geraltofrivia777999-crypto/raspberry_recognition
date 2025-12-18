#!/usr/bin/env python3
"""
Test script to verify GPIO access and gpiod installation.
"""
import sys

def test_gpiod_import():
    """Test if gpiod can be imported"""
    print("1. Testing gpiod import...")
    try:
        import gpiod
        print(f"   ✓ gpiod imported successfully (version: {gpiod.__version__ if hasattr(gpiod, '__version__') else 'unknown'})")
        return True
    except ImportError as e:
        print(f"   ✗ Failed to import gpiod: {e}")
        print("   → Install with: pip install gpiod")
        return False

def test_gpiod_api():
    """Test which gpiod API version is available"""
    print("2. Testing gpiod API version...")
    try:
        import gpiod
        if hasattr(gpiod, "LineSettings") and hasattr(gpiod, "line"):
            print("   ✓ gpiod v2 API detected (recommended)")
            return "v2"
        elif hasattr(gpiod, "Chip") and hasattr(gpiod, "LINE_REQ_DIR_OUT"):
            print("   ✓ gpiod v1 API detected (legacy)")
            return "v1"
        else:
            print("   ✗ Unknown gpiod API version")
            return None
    except Exception as e:
        print(f"   ✗ Error checking gpiod API: {e}")
        return None

def test_chip_access():
    """Test if we can access GPIO chip"""
    print("3. Testing GPIO chip access...")
    try:
        import gpiod

        chip_paths = ["/dev/gpiochip0", "gpiochip0", "/dev/gpiochip1"]
        chip = None
        chip_path = None

        for path in chip_paths:
            try:
                chip = gpiod.Chip(path)
                chip_path = path
                print(f"   ✓ Opened GPIO chip at {path}")
                break
            except (FileNotFoundError, PermissionError, OSError) as e:
                print(f"   - Cannot open {path}: {e}")
                continue

        if chip is None:
            print("   ✗ Cannot access any GPIO chip")
            print("   → Run: bash setup_gpio.sh")
            return False

        return True
    except Exception as e:
        print(f"   ✗ Error accessing GPIO chip: {e}")
        return False

def test_gpio_controller():
    """Test GPIOController initialization"""
    print("4. Testing GPIOController...")
    try:
        from gpio_controller import GPIOController

        # Try to initialize controller (won't actually control GPIO in test)
        controller = GPIOController(pin=17, pulse_ms=800)

        if controller.mode == "v2":
            print("   ✓ GPIOController initialized with gpiod v2")
            return True
        elif controller.mode == "v1":
            print("   ✓ GPIOController initialized with gpiod v1")
            return True
        elif controller.mode == "none":
            print("   ✗ GPIOController failed to initialize")
            print("   → Check permissions: bash setup_gpio.sh")
            return False

    except Exception as e:
        print(f"   ✗ Error testing GPIOController: {e}")
        return False

def main():
    print("=" * 60)
    print("GPIO Setup Test for Raspberry Pi Face Recognition")
    print("=" * 60)
    print()

    results = []

    # Run tests
    results.append(("gpiod import", test_gpiod_import()))

    if results[0][1]:  # Only continue if import succeeded
        api_version = test_gpiod_api()
        results.append(("gpiod API", api_version is not None))

        if api_version:
            results.append(("chip access", test_chip_access()))
            results.append(("GPIO controller", test_gpio_controller()))

    # Summary
    print()
    print("=" * 60)
    print("Test Summary:")
    print("=" * 60)

    all_passed = all(r[1] for r in results)

    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")

    print()

    if all_passed:
        print("✓ All tests passed! GPIO is ready to use.")
        return 0
    else:
        print("✗ Some tests failed. Please fix the issues above.")
        print()
        print("Common fixes:")
        print("1. Install gpiod: pip install gpiod")
        print("2. Setup permissions: bash setup_gpio.sh")
        print("3. Log out and back in after running setup_gpio.sh")
        return 1

if __name__ == "__main__":
    sys.exit(main())
