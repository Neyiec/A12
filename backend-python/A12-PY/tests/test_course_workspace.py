import pytest
from a12_ppt.course_graph import validate_graph
from a12_ppt.models import CourseGraphUpsertRequest
from a12_ppt.course_draft import outline_from_path

def test_course_metadata_and_observable_skills_survive_validation():
    graph = validate_graph({'subject':'科学','grade':'八年级',
        'nodes':[{'id':'k1','label':'折射','kind':'concept'},
                 {'id':'s1','label':'画光路','kind':'skill','task':'画入射与折射光线','mastery_standard':'标注角度准确'}],
        'edges':[{'source':'k1','target':'s1','relation':'supports'}]})
    assert graph['subject'] == '科学' and graph['grade'] == '八年级'
    assert graph['nodes'][1]['task'] == '画入射与折射光线'
    assert graph['nodes'][1]['assessment'] == '标注角度准确'

def test_browser_save_uses_authenticated_identity_not_required_user_id():
    request = CourseGraphUpsertRequest(course_id='course-123',title='光的折射',subject='科学',grade='八年级')
    assert request.user_id is None
    assert request.grade == '八年级'


def test_path_outline_separates_student_task_from_assessment():
    concept = {'id':'k1','label':'折射','kind':'concept'}
    skill = {'id':'s1','label':'画光路','kind':'skill','task':'画空气到水的光路','assessment':'法线与角度标注正确'}
    graph = {'title':'光的折射','course_id':'refraction','version':1,
             'edges':[{'source':'k1','target':'s1','relation':'supports'}]}
    path = {'nodes':[concept],'skills':[skill],'target_ids':['k1']}
    slide = outline_from_path(graph,path,'科学','八年级')['slides'][1]
    assert slide['student_task'] == '画空气到水的光路'
    assert slide['assessment_criteria'] == '法线与角度标注正确'
