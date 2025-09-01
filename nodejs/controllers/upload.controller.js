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
        console.log("uploading song started... ", path);
        const result = await cloudinary.uploader.upload(path, {
            folder: "songs",
            use_filename: true,
            resource_type: "video"
        });
        console.log("uploading song finished");

        return result.secure_url;
    } catch (e) {
        console.error(e);
    }
};

export const uploadImage = async path => {
    try {
        console.log("uploading image started... ", path);
        const result = await cloudinary.uploader.upload(path, {
            folder: "images",
            use_filename: true
        });
        console.log("uploading image finished");
        return result.secure_url;
    } catch (e) {
        console.error(e);
    }
};
