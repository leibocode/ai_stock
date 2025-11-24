<?php
// 数据库配置
return [
    'default' => 'mysql',
    'connections' => [
        'mysql' => [
            'type' => 'mysql',
            'hostname' => env('DATABASE.HOSTNAME', '127.0.0.1'),
            'database' => env('DATABASE.DATABASE', 'stock_review'),
            'username' => env('DATABASE.USERNAME', 'root'),
            'password' => env('DATABASE.PASSWORD', ''),
            'hostport' => env('DATABASE.HOSTPORT', '3306'),
            'charset' => 'utf8mb4',
            'prefix' => '',
            'debug' => true,
        ],
    ],
];
