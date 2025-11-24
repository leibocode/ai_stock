<?php
// 数据库连接类

class Database {
    private static $instance = null;
    private $pdo;

    private function __construct() {
        $config = require __DIR__ . '/../config/database.php';

        $dsn = sprintf(
            'mysql:host=%s;port=%d;dbname=%s;charset=%s',
            $config['host'],
            $config['port'],
            $config['database'],
            $config['charset']
        );

        $this->pdo = new PDO($dsn, $config['username'], $config['password'], [
            PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        ]);
    }

    public static function getInstance(): self {
        if (self::$instance === null) {
            self::$instance = new self();
        }
        return self::$instance;
    }

    public function getPdo(): PDO {
        return $this->pdo;
    }

    public function query(string $sql, array $params = []): array {
        $stmt = $this->pdo->prepare($sql);
        $stmt->execute($params);
        return $stmt->fetchAll();
    }

    public function execute(string $sql, array $params = []): int {
        $stmt = $this->pdo->prepare($sql);
        $stmt->execute($params);
        return $stmt->rowCount();
    }

    public function insert(string $table, array $data): int {
        $columns = implode(',', array_keys($data));
        $placeholders = implode(',', array_fill(0, count($data), '?'));

        $sql = "INSERT INTO {$table} ({$columns}) VALUES ({$placeholders})";
        $this->execute($sql, array_values($data));

        return (int) $this->pdo->lastInsertId();
    }

    public function insertBatch(string $table, array $rows): int {
        if (empty($rows)) return 0;

        $columns = implode(',', array_keys($rows[0]));
        $placeholders = '(' . implode(',', array_fill(0, count($rows[0]), '?')) . ')';
        $allPlaceholders = implode(',', array_fill(0, count($rows), $placeholders));

        $values = [];
        foreach ($rows as $row) {
            $values = array_merge($values, array_values($row));
        }

        $sql = "INSERT INTO {$table} ({$columns}) VALUES {$allPlaceholders}
                ON DUPLICATE KEY UPDATE ts_code=VALUES(ts_code)";

        return $this->execute($sql, $values);
    }
}
