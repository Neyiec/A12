package edu.zstu.service;

import cn.hutool.json.JSONUtil;
import edu.zstu.dto.*;
import edu.zstu.mapper.SysUserMapper;
import edu.zstu.vo.ProjectVO;
import jakarta.annotation.PostConstruct;
import lombok.RequiredArgsConstructor;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import java.util.*;

/** Atomic, owner-scoped and idempotent materialization of an AI batch item. */
@Service
@RequiredArgsConstructor
public class BatchProjectImportService {
    private final JdbcTemplate jdbc;
    private final ProjectService projects;
    private final SysUserMapper users;

    @PostConstruct
    public void ensureSchema() {
        jdbc.execute("""
            CREATE TABLE IF NOT EXISTS ws_batch_import (
              user_id INT NOT NULL,batch_id VARCHAR(32) NOT NULL,item_id VARCHAR(32) NOT NULL,
              project_id INT NULL,created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
              PRIMARY KEY(user_id,batch_id,item_id)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """);
    }

    public record ImportRequest(String batch_id, String item_id, String title,
                                List<Map<String,Object>> slides, Map<String,Object> metadata) {}

    @Transactional
    public ProjectVO save(Integer owner, ImportRequest request) {
        if (owner == null || owner <= 0) throw new IllegalArgumentException("请先登录");
        var user = users.findById(owner);
        if (user == null || user.getIs_active() != 1 || user.getDeleted_at() != null) throw new IllegalArgumentException("账号不可用");
        if (request.batch_id() == null || !request.batch_id().matches("[0-9a-f]{32}") || request.item_id() == null || !request.item_id().matches("[0-9a-f]{32}")) throw new IllegalArgumentException("批次标识无效");
        if (request.title() == null || request.title().isBlank() || request.title().length() > 180 || request.slides() == null || request.slides().isEmpty() || request.slides().size() > 30) throw new IllegalArgumentException("项目名称或页面数无效");
        int bytes = 0;
        for (var slide : request.slides()) {
            Object html = slide.get("html");
            if (!(html instanceof String text) || text.isBlank() || text.length() > 1_500_000) throw new IllegalArgumentException("页面 HTML 无效或过大");
            bytes += text.length();
        }
        if (bytes > 12_000_000) throw new IllegalArgumentException("章节内容过大，请减少插图体积后另建项目");
        jdbc.update("INSERT INTO ws_batch_import(user_id,batch_id,item_id) VALUES(?,?,?) ON DUPLICATE KEY UPDATE user_id=user_id", owner,request.batch_id(),request.item_id());
        var mapping = jdbc.queryForMap("SELECT project_id FROM ws_batch_import WHERE user_id=? AND batch_id=? AND item_id=? FOR UPDATE",owner,request.batch_id(),request.item_id());
        if (mapping.get("project_id") != null) {
            // Never overwrite a teacher's subsequent edits when a client retries the import.
            return projects.getProject(mapping.get("project_id").toString(),owner);
        }
        ProjectCreateDTO project = new ProjectCreateDTO();
        project.setProject_name(request.title()); project.setProject_type("ppt"); project.setStatus("editing");
        project.setEdit_history(JSONUtil.toJsonStr(Map.of("batch_id",request.batch_id(),"batch_item_id",request.item_id(),
            "generation_metadata",request.metadata()==null?Map.of():request.metadata(),
            "workspace_context",Map.of("source","batch_generation"))));
        var created = projects.createProject(project,owner);
        String projectId = String.valueOf(created.getId());
        int index = 0;
        for (var slide : request.slides()) {
            PageDTO page = new PageDTO(); page.setPage_order(++index);
            page.setPage_type(index == 1 ? "cover" : "content");
            page.setPage_title(String.valueOf(slide.getOrDefault("title","第" + index + "页")));
            page.setPage_content(JSONUtil.toJsonStr(slide)); page.setComponents("[]"); page.setAutosave(false); page.setDirty(false);
            projects.createPage(projectId,page,owner);
        }
        VersionCreateDTO snapshot = new VersionCreateDTO(); snapshot.setDescription("批量生成 · 初始快照");
        projects.saveVersion(projectId,snapshot,owner);
        jdbc.update("UPDATE ws_batch_import SET project_id=? WHERE user_id=? AND batch_id=? AND item_id=?",created.getId(),owner,request.batch_id(),request.item_id());
        return projects.getProject(projectId,owner);
    }
}
