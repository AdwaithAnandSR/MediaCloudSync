import axios from "axios";

setInterval(async () => {
    try {
        const res = await axios.get(
            "https://mediacloudsync.onrender.com/health"
        );
        console.log(res.data?.status);
    } catch (e) {
        console.log(e);
    }
}, 10000);
