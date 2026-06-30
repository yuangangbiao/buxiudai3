CREATE TABLE IF NOT EXISTS container_center.message_templates (
    id            VARCHAR(50)   NOT NULL PRIMARY KEY,
    name          VARCHAR(100)  NOT NULL,
    category      VARCHAR(20)   NOT NULL,
    title         VARCHAR(200)  DEFAULT '',
    content       TEXT          NOT NULL,
    channels      JSON          DEFAULT ('["wechat_group"]'),
    msg_type      VARCHAR(10)   DEFAULT 'markdown',
    is_builtin    TINYINT(1)    DEFAULT 0,
    is_active     TINYINT(1)    DEFAULT 1,
    version       INT           DEFAULT 1,
    created_at    DATETIME      DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME      DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
