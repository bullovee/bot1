import importlib
import pkgutil
import inspect
import traceback

# Dictionary global untuk menampung semua HELP dari tiap modul
HELP = {}

async def init(client):
    package = __name__

    for _, module_name, ispkg in pkgutil.iter_modules(__path__):
        if ispkg:
            continue

        try:
            module = importlib.import_module(f"{package}.{module_name}")

            # 🔹 Jalankan init(client) kalau ada
            if hasattr(module, "init"):
                module.init(client)
                print(f"✅ Modul {module_name} dimuat via init()")

            # 🔹 Jalankan register(client) kalau ada
            if hasattr(module, "register"):
                module.register(client)
                print(f"✅ Modul {module_name} dimuat via register()")

            # 🔹 Jalankan init_owner(client) kalau ada
            if hasattr(module, "init_owner"):
                func = module.init_owner
                if inspect.iscoroutinefunction(func):
                    try:
                        await func(client)
                    except Exception as e:
                        print(f"⚠️ Modul {module_name} gagal init_owner() (async): {e}")
                        traceback.print_exc()
                else:
                    try:
                        func(client)
                    except Exception as e:
                        print(f"⚠️ Modul {module_name} gagal init_owner() (sync): {e}")
                        traceback.print_exc()
                print(f"✅ Modul {module_name} dimuat via init_owner()")

            # 🔹 Gabungkan HELP kalau ada
            if hasattr(module, "HELP"):
                try:
                    for k, v in module.HELP.items():
                        if k not in HELP:
                            HELP[k] = []
                        HELP[k].extend(v)
                except Exception as e:
                    print(f"⚠️ Gagal menggabungkan HELP dari modul {module_name}: {e}")
                    traceback.print_exc()

        except Exception as e:
            print(f"❌ Gagal load modul {module_name}: {e}")
            traceback.print_exc()
