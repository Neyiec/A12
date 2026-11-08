package edu.zstu.controller;

import edu.zstu.service.QuestionBankService;
import edu.zstu.utils.CurrentHolder;
import edu.zstu.utils.Result;
import org.springframework.web.bind.annotation.*;
import java.util.Map;
import java.util.function.Supplier;

@RestController
public class QuestionBankController {
    private final QuestionBankService service;
    public QuestionBankController(QuestionBankService service){this.service=service;}
    private Result<?> call(Supplier<Object> action){
        if(CurrentHolder.getCurrentId()==null)return Result.error(401,"请先登录");
        try{return Result.success(action.get());}catch(IllegalArgumentException e){return Result.error(400,e.getMessage());}
    }
    @GetMapping("/api/v1/questions") public Result<?> list(@RequestParam Map<String,String> params){return call(()->service.list(CurrentHolder.getCurrentId(),false,params));}
    @GetMapping("/api/v1/questions/{id}") public Result<?> detail(@PathVariable long id){return call(()->service.detail(id,CurrentHolder.getCurrentId(),false));}
    @PostMapping("/api/v1/questions") public Result<?> create(@RequestBody Map<String,Object> body){return call(()->service.saveQuestion(null,CurrentHolder.getCurrentId(),body,false));}
    @PutMapping("/api/v1/questions/{id}") public Result<?> update(@PathVariable long id,@RequestBody Map<String,Object> body){return call(()->service.saveQuestion(id,CurrentHolder.getCurrentId(),body,false));}
    @GetMapping("/api/v1/papers") public Result<?> papers(){return call(()->service.papers(CurrentHolder.getCurrentId()));}
    @GetMapping("/api/v1/papers/{id}") public Result<?> paper(@PathVariable long id){return call(()->service.paper(id,CurrentHolder.getCurrentId()));}
    @PostMapping("/api/v1/papers") public Result<?> createPaper(@RequestBody Map<String,Object> body){return call(()->service.savePaper(null,CurrentHolder.getCurrentId(),body));}
    @PutMapping("/api/v1/papers/{id}") public Result<?> updatePaper(@PathVariable long id,@RequestBody Map<String,Object> body){return call(()->service.savePaper(id,CurrentHolder.getCurrentId(),body));}
    @GetMapping("/api/v1/admin/questions") public Result<?> adminList(@RequestParam Map<String,String> params){return call(()->service.list(CurrentHolder.getCurrentId(),true,params));}
    @GetMapping("/api/v1/admin/questions/{id}") public Result<?> adminDetail(@PathVariable long id){return call(()->service.detail(id,CurrentHolder.getCurrentId(),true));}
    @PostMapping("/api/v1/admin/questions") public Result<?> adminCreate(@RequestBody Map<String,Object> body){return call(()->service.saveQuestion(null,CurrentHolder.getCurrentId(),body,true));}
    @PostMapping("/api/v1/admin/questions/{id}/review") public Result<?> review(@PathVariable long id,@RequestBody Map<String,Object> body){return call(()->service.review(id,CurrentHolder.getCurrentId(),body));}
}
