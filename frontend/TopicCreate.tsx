import React, {useState} from 'react';
import axios from 'axios';
import ErrorMessage from '../web/ErrorMessage';
import SuccesMessage from '../web/SuccessMessage';
import TextEditor from './TextEditor';
import ImagesForm from '../draganddrop/ImagesForm';
import getCookie from '../auth/Cookie';
import { useLocation, useNavigate } from 'react-router-dom';
var csrftoken = getCookie('csrftoken');
type IErrors = {
    errors?: Array<string>;
}

const TopicCreate = () =>{
    let { state } = useLocation();
    const navigate = useNavigate();
    const [topicCreateState, setTopicCreateState] = useState({
        title: "",
        description: "",
        usdot: ""
        
    })
    const [imageState, setImageState] = useState({
        images:[]
    })

    const [errorState, setErrorState] = useState<IErrors>({
        errors: []
    });
    const [messageState, setMessageState] = useState({
        message: null
      });

    const displayErrors = () => {
        if (errorState.errors.length > 0) {
            return <ErrorMessage errors={errorState.errors} setErrorState={setErrorState}></ErrorMessage>;
        } else {
            return null;
        }
    };

    const displayMessage = () => {
        if (messageState.message) {
          return <SuccesMessage message={messageState.message}  setMessageState={setMessageState}></SuccesMessage>
        } else {
            return null;
        }
    }
    const CreateTopic = () =>{
        let formData = new FormData()
        formData.append('title', topicCreateState.title)
        formData.append('usdot', topicCreateState.usdot)
        formData.append('description', topicCreateState.description)
        formData.append('token', localStorage.auth_token)
        if (imageState.images) {
            imageState.images.forEach(function (item) {
              if (item.size ) {
                formData.append('images', item, item.name)
              }
            })
      
          }
        axios({
            method: 'post',
            url: `${process.env.API_URL}api/topics/`,
            headers:{
                'Authorization': localStorage.auth_token,
                'X-CSRFToken': csrftoken
            },
            data: formData
        })
        .then(function (response) {
            console.log(response.data.topic)
            setMessageState({
                message: response.data.message
            })
            window.location.replace(`/app/topics/${response.data.topic}`);
        
        })
        .catch(function (error) {
            setErrorState({
                "errors": [error.response.data.error]
            })
        })
    }

    const fieldListener = (event, key) =>{
        setTopicCreateState(oldstate => {
            let state_result = {
                ...oldstate,
                [key]: event.target.value,

            };
            return state_result
        })
    }
    const fieldTextListener = (value) =>{
        setTopicCreateState(oldstate => {
            let state_result = {
                ...oldstate,
                "description": value,

            };
            return state_result
        })
    }
    return(
        <div className='container'>
            <div className='company topic-create--card'>
            <h1>Create Topic</h1>
            <h3>You can create a topic about your own experience</h3>
            <br></br>
        {displayErrors()}
        {displayMessage()}
        <div className="input-group mb-3 searchContainer">
            <input onChange={e => fieldListener(e, "usdot")} id="search" type="text" className="form-control" placeholder="USDot Number..." aria-label="USDot..." aria-describedby="basic-addon2" defaultValue={state && state.usdot ? state.usdot : ""}></input>
            
            </div>
            <div className="input-group mb-3 searchContainer">
            <input onChange={e => fieldListener(e, "title")} id="search" type="text" className="form-control" placeholder="Title..." aria-label="Title..." aria-describedby="basic-addon2"></input>
            
            </div>
            <TextEditor modalListener={fieldTextListener}></TextEditor>
            <ImagesForm imageState={imageState} setImageState={setImageState} ></ImagesForm>
            {topicCreateState && topicCreateState.title && topicCreateState.description ?
                    <div onClick={() => CreateTopic()} className='topic-create--button'>Save</div>
                    :
                    <div onClick={() => {}} className='topic-create--button not-available'>Save</div>                }
            <div onClick={() => navigate(-1)} className='topic-create--button topic-create--button-back'>Go back</div>
        </div>
        </div>
    )
    
}
export default TopicCreate;
