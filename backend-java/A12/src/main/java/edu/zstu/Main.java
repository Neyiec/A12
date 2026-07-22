package edu.zstu;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;


import java.time.LocalDateTime;


//@SpringBootApplication
public class Main {
    public static void main(String[] args) {
//        SpringApplication.run(Main.class, args);
        System.out.println(LocalDateTime.now());
    }
}
