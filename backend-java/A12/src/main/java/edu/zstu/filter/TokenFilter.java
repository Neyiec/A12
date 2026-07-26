package edu.zstu.filter;


import edu.zstu.utils.CurrentHolder;
import edu.zstu.utils.JwtUtil;
import io.jsonwebtoken.Claims;
import jakarta.annotation.Resource;
import jakarta.servlet.*;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.extern.slf4j.Slf4j;

import java.io.IOException;

@Slf4j
//@WebFilter(urlPatterns = "/*")
public class TokenFilter implements Filter {
    @Resource
    private JwtUtil jwtUtil;
    @Override
    public void doFilter(ServletRequest servletRequest, ServletResponse servletResponse, FilterChain filterChain) throws IOException, ServletException {
        HttpServletRequest request=(HttpServletRequest)servletRequest;
        HttpServletResponse response=(HttpServletResponse)servletResponse;

        //获得请求路径
        String requestURI = request.getRequestURI();

        //判断是否是登录请求

        //不存在登录
        if(!requestURI.contains("/auth")){
            //查看令牌
            String BearerToken = request.getHeader("Authorization");

            if(BearerToken==null ||BearerToken.isEmpty()){
                response.getWriter().write("用户未登录");
                response.setStatus(401);
                return;
            }

            if(!BearerToken.startsWith("Bearer ")){
                response.getWriter().write("令牌格式错误");
                response.setStatus(401);
                return;
            }
            String token = BearerToken.substring(7);
            try {

                Claims claims = jwtUtil.parseToken(token);
                //将id保存到local中
                Integer id=claims.get("user_id", Integer.class);
                CurrentHolder.setCurrentId(id);
            }catch (Exception e){
                log.info("令牌非法");
                response.setStatus(401);
                return;
            }
        }
        //如果通过就放行
        filterChain.doFilter(servletRequest,servletResponse);
        CurrentHolder.remove();
    }
}
