package edu.zstu;

import cn.hutool.core.util.RandomUtil;
import edu.zstu.utils.PasswordUtil;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.mail.SimpleMailMessage;
import org.springframework.mail.javamail.JavaMailSender;

// 关键：classes 指定只加载 MailConfig，不加载主启动类
@SpringBootTest
public class test1 {

    @Autowired
    private JavaMailSender mailSender;  // 现在只注入邮件，不加载其他Bean

    @Autowired
    private PasswordUtil passwordUtil;

    @Test
    public void func2() {
        String code= RandomUtil.randomNumbers(6);
        SimpleMailMessage message = new SimpleMailMessage();
        message.setFrom("3276142066@qq.com");
        message.setTo("whn3276142066@163.com");
        message.setSubject("A12 教学平台 - 注册验证码");
        message.setText("您的验证码为："+ code+"\n有效期 60 秒，请勿泄露给他人。");

        mailSender.send(message);
        System.out.println("发送成功！");
    }

    @Test
    public void func1() {
        String password = "123456";
        String hash = passwordUtil.hash(password);
        System.out.println(hash);
    }
}