package edu.zstu.service;

import org.springframework.stereotype.Component;

import java.util.concurrent.ThreadLocalRandom;

@Component
public class CommunityReviewSampling {
    public boolean selected() {
        return ThreadLocalRandom.current().nextInt(100) < 10;
    }
}
