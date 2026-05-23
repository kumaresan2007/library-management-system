# MySQL on Windows: use PyMySQL as mysqlclient substitute when mysqlclient is unavailable.
import sys

if sys.platform == "win32":
    try:
        import pymysql  # noqa: F401

        pymysql.install_as_MySQLdb()
    except ImportError:
        pass
