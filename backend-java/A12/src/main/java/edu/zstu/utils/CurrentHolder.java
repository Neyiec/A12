package edu.zstu.utils;

public class CurrentHolder {
    private static final ThreadLocal<Integer> CURRENT_THREAD=new ThreadLocal<>();

    public static void setCurrentId(Integer param){
        CURRENT_THREAD.set(param);
    }

    public static void remove(){
        CURRENT_THREAD.remove();
    }

    public static Integer getCurrentId(){
        return CURRENT_THREAD.get();
    }
}
