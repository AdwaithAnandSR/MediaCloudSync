const videos = []

export const addVideo = (id, url) => {
    const exist = videos.find(vid => vid.id === id);
    if (!exist) {
        videos.push({
            id,
            url,
            currentStatus: "processing...",
            status: "PROCESSING",
            type: "video"
        });
    }
};

export const getVideos = () => {
    return videos;
};

export const updateStatus = (id, updates)=>{
    const video = videos.find(vid=> vid.id === id)
    if(video){
        Object.assign(video, updates)
        if(updates?.status === "FAIL" || updates?.status === "SUCCESS"){
            if(video.audioPath && video.coverPath){
                fs.unlinkSync(video.audioPath);
                fs.unlinkSync(video.coverPath);
                console.log("files deleted successfully");
            }
        }
    }else{
        console.log("update video failed for id: ", id)
    }
}

export const generateId = () => {
  return Date.now().toString();
}

