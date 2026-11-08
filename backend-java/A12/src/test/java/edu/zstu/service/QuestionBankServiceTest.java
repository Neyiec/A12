package edu.zstu.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.springframework.jdbc.datasource.DataSourceTransactionManager;
import org.springframework.aop.framework.ProxyFactory;
import org.springframework.transaction.interceptor.TransactionInterceptor;
import org.springframework.transaction.annotation.AnnotationTransactionAttributeSource;
import java.util.*;
import static org.junit.jupiter.api.Assertions.*;

class QuestionBankServiceTest {
    QuestionBankService service;
    JdbcTemplate db;
    @BeforeEach void setup(){
        String mysql=System.getenv("A12_QB_TEST_JDBC_URL");
        if(mysql!=null&&!mysql.matches("jdbc:mysql://127\\.0\\.0\\.1:3306/a12_qb_test_[a-f0-9]+\\?.*"))throw new IllegalArgumentException("真实 MySQL 测试只允许隔离的 a12_qb_test_ 数据库");
        var source=mysql==null?new DriverManagerDataSource("jdbc:h2:mem:"+UUID.randomUUID()+";MODE=MySQL;DATABASE_TO_LOWER=TRUE;DB_CLOSE_DELAY=-1","sa",""):new DriverManagerDataSource(mysql,System.getenv("A12_QB_TEST_USER"),System.getenv("A12_QB_TEST_PASSWORD"));
        db=new JdbcTemplate(source);var target=new QuestionBankService(db,new ObjectMapper());target.initialize();
        if(mysql!=null){db.update("DELETE FROM qb_review");db.update("DELETE FROM qb_paper");db.update("DELETE FROM qb_question");}
        var factory=new ProxyFactory(target);factory.setProxyTargetClass(true);
        factory.addAdvice(new TransactionInterceptor(new DataSourceTransactionManager(source),new AnnotationTransactionAttributeSource()));
        service=(QuestionBankService)factory.getProxy();
    }
    Map<String,Object> body(String action){return new LinkedHashMap<>(Map.of("subject","数学","grade","初二","question_type","single","difficulty","easy","stem","直角三角形两直角边为3和4，斜边长为？","options",List.of("5","7"),"answer","A","analysis","由勾股定理得到5","action",action));}
    long id(Map<String,Object> q){return ((Number)q.get("id")).longValue();}
    @Test void draftPrivateAndSubmissionRequiresReview(){
        var q=service.saveQuestion(null,1,body("draft"),false);
        long draftId=id(q);
        assertThrows(IllegalArgumentException.class,()->service.detail(draftId,2,false));
        assertEquals(0L,service.list(1,false,Map.of()).get("total"));
        var input=body("submit");input.put("revision",q.get("revision"));
        q=service.saveQuestion(id(q),1,input,false);long qid=id(q);
        assertEquals("pending",q.get("status"));
        var approved=service.review(qid,9,Map.of("decision","approved","revision",q.get("revision")));
        assertEquals("approved",approved.get("status"));assertEquals(1L,service.list(2,false,Map.of()).get("total"));
        assertEquals(1,((List<?>)approved.get("reviews")).size());
    }
    @Test void teacherCannotPublishOrEditOthers(){
        assertThrows(IllegalArgumentException.class,()->service.saveQuestion(null,1,body("publish"),false));
        var q=service.saveQuestion(null,1,body("draft"),false);var update=body("draft");update.put("revision",1);
        assertThrows(IllegalArgumentException.class,()->service.saveQuestion(id(q),2,update,false));
    }
    @Test void invalidAnswersAndIncompleteSubmissionRejected(){
        var input=body("submit");input.put("answer","C");assertThrows(IllegalArgumentException.class,()->service.validateQuestion(input,true));
        input.put("answer","A");input.put("analysis","");assertThrows(IllegalArgumentException.class,()->service.validateQuestion(input,true));
        input.put("analysis","解析");input.put("question_type","multiple");assertThrows(IllegalArgumentException.class,()->service.validateQuestion(input,true));
        input.put("answer","A,B");assertDoesNotThrow(()->service.validateQuestion(input,true));
    }
    @Test void rejectMustGiveReasonAndRevisionPreventsDoubleReview(){
        var q=service.saveQuestion(null,1,body("submit"),false);
        assertThrows(IllegalArgumentException.class,()->service.review(id(q),9,Map.of("decision","rejected","revision",1)));
        var rejected=service.review(id(q),9,Map.of("decision","rejected","note","请补充条件","revision",1));
        assertEquals("请补充条件",rejected.get("review_note"));
        assertThrows(IllegalArgumentException.class,()->service.review(id(q),9,Map.of("decision","approved","revision",1)));
        var resubmit=body("submit");resubmit.put("revision",rejected.get("revision"));assertEquals("pending",service.saveQuestion(id(q),1,resubmit,false).get("status"));
    }
    Map<String,Object> paperBody(long qid){return new LinkedHashMap<>(Map.of("title","单元练习","subject","数学","duration_minutes",45,"items",List.of(Map.of("question_id",qid,"score",3))));}
    @Test void paperFreezesContentAndIsPrivate(){
        var q=service.saveQuestion(null,9,body("publish"),true);long qid=id(q);
        var p=service.savePaper(null,1,paperBody(qid));
        assertThrows(IllegalArgumentException.class,()->service.paper(id(p),2));
        service.review(qid,9,Map.of("decision","withdrawn","note","待检查","revision",q.get("revision")));
        var next=paperBody(qid);next.put("revision",p.get("revision"));
        assertDoesNotThrow(()->service.savePaper(id(p),1,next));
        assertThrows(IllegalArgumentException.class,()->service.savePaper(null,2,paperBody(qid)));
        assertThrows(IllegalArgumentException.class,()->service.savePaper(id(p),1,next));
    }
    @Test void paperRejectsDuplicateCrossSubjectAndInvalidScores(){
        var q=service.saveQuestion(null,9,body("publish"),true);var input=paperBody(id(q));
        input.put("items",List.of(Map.of("question_id",id(q),"score",3),Map.of("question_id",id(q),"score",4)));
        assertThrows(IllegalArgumentException.class,()->service.savePaper(null,1,input));
        input.put("items",List.of(Map.of("question_id",id(q),"score",0)));assertThrows(IllegalArgumentException.class,()->service.savePaper(null,1,input));
        input.put("items",List.of(Map.of("question_id",id(q),"score",3)));input.put("subject","化学");assertThrows(IllegalArgumentException.class,()->service.savePaper(null,1,input));
    }
    @Test void filtersCannotReadDraftsOrInjectSql(){
        service.saveQuestion(null,9,body("publish"),true);service.saveQuestion(null,9,body("draft"),false);
        assertEquals(1L,service.list(1,false,Map.of("subject","数学","grade","初二","keyword","直角")).get("total"));
        assertEquals(0L,service.list(1,false,Map.of("subject","' OR 1=1 --")).get("total"));
        assertEquals(1L,service.list(1,false,Map.of("status","draft")).get("total"));
    }
    @Test void partialPaperFailureRollsBackAndInvalidInputIsRejected(){
        var q=service.saveQuestion(null,9,body("publish"),true);var input=paperBody(id(q));
        input.put("duration_minutes","invalid");assertThrows(IllegalArgumentException.class,()->service.savePaper(null,1,input));
        input.put("duration_minutes",45);input.put("items",List.of(Map.of("question_id",id(q),"score",3),Map.of("question_id",9999,"score",5)));
        assertThrows(IllegalArgumentException.class,()->service.savePaper(null,1,input));
        assertEquals(0,service.papers(1).size());
    }
    @Test void incompleteDraftCanSaveButCannotSubmitOrEnterPaper(){
        var input=body("draft");input.put("stem","");input.put("options",List.of("",""));input.put("answer","");input.put("analysis","");
        var q=service.saveQuestion(null,1,input,false);
        assertEquals("draft",q.get("status"));
        assertThrows(IllegalArgumentException.class,()->service.savePaper(null,1,paperBody(id(q))));
        input.put("action","submit");input.put("revision",1);assertThrows(IllegalArgumentException.class,()->service.saveQuestion(id(q),1,input,false));
    }
}
