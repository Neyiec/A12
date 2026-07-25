package edu.zstu.service;

import edu.zstu.dto.*;
import edu.zstu.vo.LoginVO;
import edu.zstu.vo.UserVO;

public interface AuthService {
    UserVO register(RegisterDTO dto);
    LoginVO login(LoginDTO dto);
    void sendVerificationCode(VerificationCodeDTO dto);
    void verify(VerifyDTO dto);
    LoginVO initialPasswordChange(InitialPasswordChangeDTO dto);
    void passwordReset(PasswordResetDTO dto);
    void logout(String authorization);
}
