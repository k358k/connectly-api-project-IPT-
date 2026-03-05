from singletons.config_manager import ConfigManager

# Create two variables calling the Singleton
config1 = ConfigManager()
config2 = ConfigManager()

# Verify both variables point to the same memory address
print(f"Is config1 the same instance as config2? {config1 is config2}")
assert config1 is config2  # If this fails, the Singleton is broken

# Change a setting in one and check the other
config1.set_setting("DEFAULT_PAGE_SIZE", 50)
print(f"Config2 page size updated to: {config2.get_setting('DEFAULT_PAGE_SIZE')}")
assert config2.get_setting("DEFAULT_PAGE_SIZE") == 50

print("SUCCESS: Singleton pattern verified.")