package edu.zstu.controller;

import edu.zstu.mapper.SysRoleMapper;
import edu.zstu.utils.CurrentHolder;
import edu.zstu.utils.Result;
import org.springframework.web.bind.annotation.*;
import java.util.*;

/** Stable menu contract for the two frontends. Menus do not replace API authorization. */
@RestController
@RequestMapping("/api/v1/menu")
public class MenuController {
    private final SysRoleMapper roles;
    public MenuController(SysRoleMapper roles) { this.roles=roles; }
    private Map<String,String> item(String path,String component,String label) {
        return Map.of("path","/main/"+path,"component",component,"label",label);
    }
    @GetMapping("/routers")
    public Result<?> routers(@RequestParam(defaultValue="teacher") String client) {
        Integer user=CurrentHolder.getCurrentId();if(user==null)return Result.error(401,"请先登录");
        List<Map<String,String>> menus=new ArrayList<>();
        if(client.equals("teacher")) {
            menus.add(item("workspace","WorkspaceEntry","个人工作台"));
            menus.add(item("resources","ResourceLibrary","个人资源库"));
            menus.add(item("community","CommunityHub","技能与案例"));
            menus.add(item("courses","CourseGraphWorkspace","课程双图谱"));
            menus.add(item("questions","QuestionBank","题库与组卷"));
            menus.add(item("exports","ExportCenter","成果导出中心"));
            menus.add(item("settings","AccountSettings","账号与安全"));
        } else if(client.equals("admin")) {
            List<String> permissions=Optional.ofNullable(roles.findPermCodesByUserId(user)).orElse(List.of());
            if(permissions.contains("dashboard:view"))menus.add(item("dashboard","Dashboard","数据看板"));
            if(permissions.contains("audit:view"))menus.add(item("audit","ContentAudit","内容审核"));
            if(permissions.contains("audit:view")||permissions.contains("resources:edit"))menus.add(item("questions","QuestionManagement","题库录入与审核"));
            if(permissions.contains("resources:view"))menus.add(item("resources","ResourceKnowledge","公共资源"));
            if(permissions.contains("users:view"))menus.add(item("users","UserPermission","用户管理"));
            if(permissions.contains("roles:view"))menus.add(item("roles","RoleManagement","角色管理"));
            if(permissions.contains("settings:view"))menus.add(item("settings","SystemSettings","系统配置"));
        } else return Result.error(400,"无效的客户端类型");
        return Result.success(Map.of("menus",menus));
    }
}
