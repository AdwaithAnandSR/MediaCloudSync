import { v2 as cloudinary } from "cloudinary";
import { config } from "dotenv";
config();

cloudinary.config({
    cloud_name: process.env.CLOUDINARY_CLOUD_NAME,
    api_key: process.env.CLOUDINARY_API_KEY,
    api_secret: process.env.CLOUDINARY_API_SECRET
});

// console.log(await cloudinary.api.ping())

export const uploadSong = async path => {
    try {
        const result = await cloudinary.uploader.upload(path, {
            folder: "songs",
            use_filename: true,
            resource_type: "video"
        });
        
        return result.secure_url;
    } catch (e) {
        console.error(e);
    }
};

export const uploadImage = async path => {
    try {
        const result = await cloudinary.uploader.upload(path, {
            folder: "images",
            use_filename: true
        });
        return result.secure_url;
    } catch (e) {
        console.error(e);
    }
};
