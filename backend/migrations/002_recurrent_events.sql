-- 复发事件（可修复灯带 MCF）研究的增量迁移。
-- 全新库由 ORM metadata 直接建表；本脚本供已有库审查升级。

-- 复发事件流：故障 / 修复 / 永久退出（与终态 followup_events 独立）
CREATE TABLE IF NOT EXISTS repair_events (
    id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    specimen_id BIGINT NOT NULL,
    kind VARCHAR(16) NOT NULL,
    event_time DOUBLE NOT NULL,
    received_seq INT NOT NULL,
    note TEXT,
    CONSTRAINT fk_repair_specimen FOREIGN KEY (specimen_id) REFERENCES specimens (id)
) DEFAULT CHARSET=utf8mb4;
CREATE INDEX repair_specimen_seq_idx ON repair_events (specimen_id, received_seq);
CREATE INDEX repair_specimen_time_idx ON repair_events (specimen_id, event_time);

-- 复发研究
CREATE TABLE IF NOT EXISTS recurrent_runs (
    id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    cohort_a_id BIGINT NOT NULL,
    cohort_b_id BIGINT NOT NULL,
    cutoff_hours DOUBLE NOT NULL DEFAULT 1450,
    confidence DOUBLE NOT NULL DEFAULT 0.95,
    status VARCHAR(24) NOT NULL DEFAULT 'queued',
    result JSON,
    error TEXT,
    owner VARCHAR(100) NOT NULL,
    created_at VARCHAR(64) NOT NULL,
    CONSTRAINT fk_rec_cohort_a FOREIGN KEY (cohort_a_id) REFERENCES test_cohorts (id),
    CONSTRAINT fk_rec_cohort_b FOREIGN KEY (cohort_b_id) REFERENCES test_cohorts (id)
) DEFAULT CHARSET=utf8mb4;

-- 维护建议支持关联复发研究；run_id 放宽为可空，旧终态研究数据保持不变
ALTER TABLE maintenance_notes MODIFY run_id BIGINT NULL;
ALTER TABLE maintenance_notes
    ADD COLUMN recurrent_run_id BIGINT NULL AFTER run_id;
ALTER TABLE maintenance_notes
    ADD CONSTRAINT fk_note_recurrent FOREIGN KEY (recurrent_run_id) REFERENCES recurrent_runs (id);
CREATE INDEX note_recurrent_status_idx ON maintenance_notes (recurrent_run_id, status);
