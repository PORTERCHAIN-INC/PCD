"""orders_write is an organization permission; admin checks must use platform ``orders``."""
import re
from pathlib import Path

from porterchain_api.admin_engine import rbac


def test_every_alias_targets_a_platform_permission() -> None:
    zed = (Path(rbac.__file__).parents[1] / "authz" / "schema.zed").read_text()
    platform = re.search(r"definition platform \{(.*?)\n\}", zed, re.S).group(1)
    perms = set(re.findall(r"permission (\w+)", platform))
    assert "orders_write" not in perms
    for target in rbac._MODULE_ALIASES.values():  # noqa: SLF001
        assert target in perms
