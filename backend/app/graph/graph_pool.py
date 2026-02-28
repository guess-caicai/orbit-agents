from neo4j import GraphDatabase


# 定义链接池类
class Neo4jPool:
    _driver = None

    def __init__(self, url, user, password, database, pool_size=20):
        self.url = url
        self.user = user
        self.password = password
        self.database = database
        self.pool_size = pool_size

    # 创建neo4j驱动
    def create_driver(self):
        if self._driver is None:
            self._driver = GraphDatabase.driver(
                self.url,
                database=self.database,
                auth=(self.user, self.password),
                max_connection_pool_size=self.pool_size
            )
        return self._driver

    def close(self):
        if self._driver:
            self._driver.close()
            self._driver = None

    def session(self):
        return self._driver.session()
