import React, { FunctionComponent, useState, useEffect } from "react";
import Image from "./Image";

interface IImageGallery {
  parent_image: any;
}

interface IImage {
  id: number;
  width: number;
  height: number;
  original: string;
  alt: string;
}

type Props = {
  images: Array<any>;
}

const ImageGallery: FunctionComponent<Props> = ({images}) => {
  const [ImageGalleryStates, setImageGalleryStates] = useState<IImageGallery>({
    parent_image: null,
  });

  useEffect(() => {
    if (images) {
      setImageGalleryStates({ ...ImageGalleryStates, parent_image: images[0] });
    }
}, [images])

  const currentImageListener = (image: IImage) => {
    setImageGalleryStates({ ...ImageGalleryStates, parent_image: image });
  };

  return (
    <div className="col-12 col-lg-5 p-0">
      <img
        className="rounded-lg img-fluid d-block mx-auto imagegallery_image"
        src={
          ImageGalleryStates.parent_image
            ? ImageGalleryStates.parent_image.url
            : null
        }
        alt={
          ImageGalleryStates.parent_image
            ? ImageGalleryStates.parent_image.alt
            : null
        }
      ></img>
      <div className="d-flex justify-content-center align-items-center mt-4">
        {images
          ? images.map(item => (
              <Image onClick={currentImageListener} key={item.id} item={item} />
            ))
          : <div className="loader"></div>}
      </div>
    </div>
  );
};
export default ImageGallery;
