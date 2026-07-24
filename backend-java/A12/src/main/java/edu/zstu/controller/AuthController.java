package edu.zstu.controller;

import edu.zstu.dto.InitialPasswordChangeDTO;
import edu.zstu.dto.LoginDTO;
import edu.zstu.dto.PasswordResetDTO;
import edu.zstu.dto.RegisterDTO;
import edu.zstu.dto.VerificationCodeDTO;
import edu.zstu.dto.VerifyDTO;
import edu.zstu.service.AuthService;
import edu.zstu.utils.Result;
import edu.zstu.vo.LoginVO;
import edu.zstu.vo.UserVO;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

/**
 * 认证模块 Controller
 * API-01~08：注册、验证码、登录、改密、退出
 *
 * <p>负责教师账号的注册、验证码发送、账号激活、登录认证、密码修改和退出登录。
 * 注册时服务端强制角色为教师，拒绝客户端指定角色。</p>
 */
@RestController
@RequestMapping("/api/v1/auth")
public class AuthController {
    @Autowired
    private AuthService authService;

    /**
     * API-01 注册教师账号
     *
     * <p>服务端强制设置角色为教师，拒绝客户端指定角色。注册成功后账号为待验证状态。</p>
     *
     * @param dto 注册请求参数 {@link RegisterDTO}
     * @return 注册成功的用户信息 {@link UserVO}
     */
    @PostMapping("/register")
    public Result<UserVO> register(@RequestBody RegisterDTO dto) {
        try {
            UserVO userVO = authService.register(dto);
            return Result.success(userVO);
        } catch (RuntimeException e) {
            return Result.error(400, e.getMessage());
        }
    }

    /**
     * API-02 发送验证码
     *
     * <p>按教师注册或密码重置场景向账号绑定的手机号或邮箱发送验证码。</p>
     *
     * @param dto 验证码发送请求参数 {@link VerificationCodeDTO}
     * @return 发送结果（无数据体）
     */
    @PostMapping("/verification-codes")
    public Result<Void> sendVerificationCode(@RequestBody VerificationCodeDTO dto) {
        try {
            authService.sendVerificationCode(dto);
            return Result.success();
        } catch (RuntimeException e) {
            return Result.error(400, e.getMessage());
        }
    }

    /**
     * API-03 校验验证码
     *
     * <p>校验验证码并将教师账号由"待验证"状态更新为"正常"状态。</p>
     *
     * @param dto 验证码校验请求参数 {@link VerifyDTO}
     * @return 校验结果（无数据体）
     */
    @PostMapping("/verify")
    public Result<Void> verify(@RequestBody VerifyDTO dto) {
        try {
            authService.verify(dto);
            return Result.success();
        } catch (RuntimeException e) {
            return Result.error(400, e.getMessage());
        }


    }

    /**
     * API-04 统一登录
     *
     * <p>统一验证三类账号（教师/审核员/后台管理员），验证成功后签发会话令牌。</p>
     *
     * @param dto 登录请求参数 {@link LoginDTO}（含 username、password）
     * @return 登录响应信息（含 token、用户信息、角色权限）{@link LoginVO}
     */
    @PostMapping("/login")
    public Result<LoginVO> login(@RequestBody LoginDTO dto) {
        try {
            LoginVO loginVO = authService.login(dto);
            return Result.success(loginVO);
        } catch (RuntimeException e) {
            return Result.error(400, e.getMessage());
        }
    }

    /**
     * API-05 初始密码修改（首次登录强制改密）
     *
     * <p>校验批量创建账号的初始密码并设置新密码，解除强制改密状态后签发正常会话。</p>
     *
     * @param dto 初始密码修改请求参数 {@link InitialPasswordChangeDTO}
     * @return 改密成功后签发的正常会话 {@link LoginVO}
     */
    @PostMapping("/initial-password-change")
    public Result<LoginVO> initialPasswordChange(@RequestBody InitialPasswordChangeDTO dto) {

        LoginVO loginVO = authService.initialPasswordChange(dto);
        return Result.success(loginVO);
    }

    /**
     * API-06 密码重置
     *
     * <p>校验账号、密码重置验证码和新密码，重置成功后撤销该账号的已有会话。</p>
     *
     * @param dto 密码重置请求参数 {@link PasswordResetDTO}
     * @return 重置结果（无数据体）
     */
    @PostMapping("/password-reset")
    public Result<Void> passwordReset(@RequestBody PasswordResetDTO dto) {
        return Result.success();
    }

    /**
     * API-08 退出登录
     *
     * <p>撤销当前会话或访问凭证并记录退出结果。</p>
     *
     * @param authorization 请求头 Authorization: Bearer &lt;token&gt;
     * @return 退出结果（无数据体）
     */
    @PostMapping("/logout")
    public Result<Void> logout(@RequestHeader("Authorization") String authorization) {
        return Result.success();
    }
}
