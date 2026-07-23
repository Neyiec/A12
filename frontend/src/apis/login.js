import {post,get} from '../utils/api'

export function login(user){
  return post('/api/user/login',user);
}

export function getRouters(){
  return get('/api/getRouters');
}