import React, { FunctionComponent, useState, useCallback, useEffect, useRef } from 'react';

type Props = {
    fileUpload?: any;
    imageState?: any;
    setImageState?: any;
    errorProductState?: any;
}


const ImagesForm: FunctionComponent<Props> = ({ imageState, setImageState, errorProductState }) => {

    const fileUploadListener = (event: any) => {
        let image_count = imageState.images.length
        const file_obj = event.target.files[0]
        const image_obj = {
            obj: "",
            url: window.URL.createObjectURL(file_obj),
            id: image_count,
            key: image_count,
            new: true

        }
        const new_file = Object.assign(file_obj, image_obj)
        setImageState(oldstate => ({ ...oldstate, images: [...oldstate.images, new_file] }))
    };
    const fieldListener = (event: any, index) => {
        event.persist();
        const indo = imageState.images.indexOf(imageState.images[index])
        imageState.images.splice(indo, 1)
        setImageState(oldstate => {

            let r = {
                ...oldstate,
                images: imageState.images
            };
            return r
        })
    };

    return (
        <>
            {imageState.images ?
                <div className="image-images">
                    {
                        imageState.images.map((item, i) => (
                            <div className='image-form-div' key={i}>
                                <img src={item.url} alt="" className=""></img>
                                <i onClick={event => fieldListener(event, i)} className="fa-solid fa-circle-xmark"></i>
                            </div>
                        ))

                    }



                </div>
                :
                <></>
            }
            {imageState.images.length < 6 ?
                <>
                    <input accept=".jpg,.jpeg,.png" id="file" className="inputfile" onChange={fileUploadListener} type="file" name="images"></input>
                    <label className="btn btn-primary" id="upload-photo-label" htmlFor="file"><i className="fas fa-cloud-upload-alt"></i>&nbsp; <span>Upload image</span></label>
                </>
                : null
            }
        </>
    )
}

export default ImagesForm;
