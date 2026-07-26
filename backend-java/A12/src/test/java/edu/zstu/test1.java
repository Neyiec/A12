package edu.zstu;

import org.junit.jupiter.api.Test;

import java.util.Date;

public class test1 {


    @Test
    public void func1() {
        String  str="hello world";
        System.out.println(str.substring(6));
        System.out.println(str.substring(1));
        System.out.println(str.startsWith("hello"));

    }

    @Test
    public void func2() {
        // 1000毫秒=1秒  1秒*60 * 60 * 24 *7 =1周（7天）
        long EXPIRATION_MS = 7 * 24 * 60 * 60 * 1000L;
        Date now = new Date();
        System.out.println(now.getTime());
        Date expiration = new Date(now.getTime() + EXPIRATION_MS);
        System.out.println(expiration);
    }
}
