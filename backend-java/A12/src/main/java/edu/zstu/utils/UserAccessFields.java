package edu.zstu.utils;
import java.util.List;
/** User type is a compatibility label; detailed authorization always uses permission codes. */
public final class UserAccessFields {
    private UserAccessFields() {}
    public static String userType(List<String> roleCodes) {
        if(roleCodes.contains("admin")||roleCodes.contains("super_admin"))return "admin";
        return roleCodes.isEmpty()?"teacher":roleCodes.get(0);
    }
}
